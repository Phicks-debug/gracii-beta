
import os
import logging
import random
import asyncio
from re import M
import boto3
import aiohttp
import xml.etree.ElementTree as ET
import concurrent.futures
import multiprocessing


from datetime import date
from bedrock_llm import Agent
from bedrock_llm.schema import ToolMetadata, InputSchema, PropertyAttr
from bedrock_llm.monitor import monitor_async
from vnstock3 import Vnstock
from ogoogles import OGoogleS, SearchResult
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from termcolor import cprint

from dotenv import load_dotenv
from bedrock_llm import AsyncClient, ModelConfig, ModelName
from bedrock_llm.schema import MessageBlock
import google.generativeai as genai
from typing import List

# Load environemnt variables
load_dotenv()
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))

vnstock = Vnstock()
searcher = OGoogleS()
runtime = boto3.client("bedrock-agent-runtime", region_name="us-east-1")
critic_model = genai.GenerativeModel(
    "gemini-1.5-flash-002",
    system_instruction="""You are the browser critic, you task is to based on the search results to decide which website, 
links should we investigate futher to answer the question. If you decide to investigate futher links then return the links in the format: ["links 1", "link 2", ... "link n"]. 
The list should only contain 2 to 5 string of relavant urls that you want to further investigate. You can include more urls than 5 but it is not encourage, only do it if nessasary. DO NOT RETURN ANYTHING ELSE.
If you decide not to investigate further links then return the string: "No further investigation needed".
Return the summarizatino for all the links if no need to investigate futher links."""
)

# Set up API
summary_model = AsyncClient(
    region_name="us-east-1",
    model_name=ModelName.CLAUDE_3_HAIKU
)
config = ModelConfig(
    temperature=0.4,
    top_p=0.9,
    max_tokens=2048
)
# Configure logging for the main process
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - Process:%(processName)s - %(message)s',
    handlers=[
        logging.FileHandler('web_processing.log'),
        logging.StreamHandler()
    ]
)


tool_get_stock_price = ToolMetadata(
    name="get_stock_price",
    description="Use this tool to retrieve the historical stock price data for a specific company.\
                This tool will get the open high low close value of the ticker.\
                The tool has been set to take the price until today and 1 month behind as default.\
                If the user do not specify the date, always get the price for the latest date.",
    input_schema=InputSchema(
        type="object",
        properties={
            "ticker": PropertyAttr(
                type="string",
                description="The stock ticker symbol of the company (e.g., A32, AAA, TCB, ...).",
            ),
            "start": PropertyAttr(
                type="string",
                description="The start date for retrieving stock data, in YYYY-MM-DD format.",
            ),
            "end": PropertyAttr(
                type="string",
                description="The end date for retrieving stock data, in YYYY-MM-DD format.",
            ),
        },
        required=["ticker", "start", "end"],
    ),
)


tool_get_stock_intraday = ToolMetadata(
    name="get_stock_intraday",
    description="Use this tool to get intraday stock data for a specific company for the closest day until today.\
                This tool will output the price in hours to minutes level of the stock. \
                ONLY use when the users ask questions related to intraday stock price or for technical analysis questions.",
    input_schema=InputSchema(
        type="object",
        properties={
            "ticker": PropertyAttr(
                type="string",
                description="The stock ticker symbol of the company (e.g., A32, AAA, TCB, ...).",
            ),
        },
        required=["ticker"],
    ),
)


tool_search_stocks_by_groups = ToolMetadata(
    name="search_stocks_by_groups",
    description="Use this tool to get a list of stock symbols belonging to a specific market group in Vietnam.\
                The tool will return stocks in groups like VN30, HOSE, HNX, VN100, or UPCOM.\
                For large groups like HOSE, HNX, or VN100, it will prioritize showing VN30 stocks.\
                For UPCOM, it will randomly select 10 stocks to display.",
    input_schema=InputSchema(
        type="object",
        properties={
            "group": PropertyAttr(
                type="string",
                description="The market group name (e.g., VN30, HOSE, HNX, VN100, UPCOM).",
            ),
        },
        required=["group"],
    ),
)


tool_retrieve_hr_policy = ToolMetadata(
    name="retrieve_hr_policy",
    description="Use this tool to retrieve the human resource policy for a TechX company.",
    input_schema=InputSchema(
        type="object",
        properties={
            "query": PropertyAttr(
                type="string",
                description="The query to retrieve the human resource policy.",
            ),
        },
        required=["query"],
    ),
)


web_browsing = ToolMetadata(
    name="web_suff",
    description="""Use this tool to browse the web and retrieve information from internet.
This tool is useful when you need to look up recent information that might not be included in the knowledge base. Use this tool for any search information on the internet that you need.""",
    input_schema=InputSchema(
        type="object",
        properties={
            "query": PropertyAttr(
                type="string",
                description="The query to search the web.",
            ),
        },
        required=["query"],
    ),
)


@Agent.tool(tool_get_stock_price)
async def get_stock_price(ticker: str, start: str, end: str = None):
    try:
        end = end or date.today().strftime("%Y-%m-%d")
        stock = vnstock.stock(symbol=ticker, source="TCBS")
        price_df = await asyncio.to_thread(stock.quote.history, start=start, end=end)
        return str(price_df.to_dict())
    except Exception as e:
        return f"Error fetching stock price data: {str(e)}"

@Agent.tool(tool_get_stock_intraday)
async def get_stock_intraday(ticker: str):
    try:
        stock = vnstock.stock(symbol=ticker, source="TCBS")
        df = await asyncio.to_thread(stock.quote.intraday, symbol=ticker, show_log=False)
        df["ticker"] = ticker
        return str(df.to_dict())
    except Exception as e:
        return f"Error fetching intraday data: {str(e)}"

@Agent.tool(tool_search_stocks_by_groups)
async def search_stocks_by_groups(group: str = "VN30"):
    try:
        group = group.upper()
        stock = vnstock.stock(symbol="VCI", source="TCBS")
    
        async def get_symbols(group_name):
            return await asyncio.to_thread(
                lambda: stock.listing.symbols_by_group(group_name).tolist()
        )

        if group == "VN30":
                return str(await get_symbols(group))
        original_list = await get_symbols(group)
        if group in ["HOSE", "HNX", "VN100"]:
            vn30_list = await get_symbols("VN30")
            stock_list = list(set(original_list) & set(vn30_list))
            return f"VN30 priority stocks in {group}: {str(stock_list)}"
        else:
            random_stocks = random.sample(original_list, min(10, len(original_list)))
            return f"Random 10 stocks from {group}: {str(random_stocks)}"
    except Exception as e:
        return f"Error searching stocks by group: {str(e)}"
    
@Agent.tool(tool_retrieve_hr_policy)
async def retrieve_hr_policy(query: str):
    kwargs = {
        "knowledgeBaseId": "20GE0TB6RJ",  # Insert your knowledge base ID
        "retrievalConfiguration": {
            "vectorSearchConfiguration": {"numberOfResults": 25}
        },
        "retrievalQuery": {"text": query},
    }

    # Run boto3 call in a thread pool since it's blocking
    result = runtime.retrieve(**kwargs)
    return build_context_kb_prompt(result)

def build_context_kb_prompt(
    retrieved_json_file, min_relevant_percentage: float = 0.5, debug=False
):
    if not retrieved_json_file:
        return ""

    documents = ET.Element("documents")

    if retrieved_json_file["ResponseMetadata"]["HTTPStatusCode"] != 200:
        documents.text = (
            "Error in getting data source from knowledge base. No context is provided"
        )
    else:
        body = retrieved_json_file["retrievalResults"]
        for i, context_block in enumerate(body):
            if context_block["score"] < min_relevant_percentage:
                break
            document = ET.SubElement(documents, "document", {"index": str(i + 1)})
            source = ET.SubElement(document, "source")
            content = ET.SubElement(document, "document_content")
            source.text = iterate_through_location(context_block["location"])
            content.text = context_block["content"]["text"]

    return ET.tostring(documents, encoding="unicode", method="xml")

def iterate_through_location(location: dict):
    # Optimize by stopping early if uri or url is found
    for loc_data in location.values():
        if isinstance(loc_data, dict):
            uri = loc_data.get("uri")
            if uri:
                return uri
            url = loc_data.get("url")
            if url:
                return url
    return None

async def web_browser(query: str):
    return await searcher.search(
        query=query,
        max_results=10,
        extract_text=False,
        max_text_length=200
    )

async def process_single_result_async(user_question: str, search_result: SearchResult):
    logger = setup_logger()
    process_name = multiprocessing.current_process().name
    # logger.info(f"Process {process_name} starting to process URL: {search_result.href}")

    """Async part of processing a single result"""
    buffer = ""
    url = search_result.href
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(
                    total=10,
                    connect=10/2,
                    sock_read=10/2
                )
            ) as response:
                if response.status != 200:
                    logger.error(f"Process {process_name} - Failed to fetch URL: {search_result.href} - Status: {response.status}")
                    return {
                        "title": search_result.title,
                        "url": search_result.href,
                        "abstract": search_result.abstract,
                        "summary": f"Error: Could not fetch content (Status {response.status})"
                    }
                buffer = await response.text(errors='ignore')
                prompt = f"""Extract relevant information about user's query: {user_question} from this HTML content source.

HTML Content: 

{buffer[:100000]}

Note: Make sure the information can answer 100% the user's question. The information should contain facets, numbers, and statistics if available.
to support the answer.
Do not summarize. Only Extract and return the relevant information.
"""
                # logger.info(f"Process {process_name} - Sending content to LLM for processing")
                async with summary_model as m:
                    async for _,_,response in m.generate_async(
                        prompt=prompt,
                        config=config
                    ):
                        pass
                
                # logger.info(f"Process {process_name} - Successfully generated summary")
                
                return {
                    "title": search_result.title,
                    "url": search_result.href,
                    "abstract": search_result.abstract,
                    "summary": response.content[0].text
                }
    except aiohttp.ClientError as e:
        logger.error(f"Process {process_name} - Network error for {search_result.href}: {str(e)}")
        return {
            "title": search_result.title,
            "url": search_result.href,
            "abstract": search_result.abstract,
            "summary": f"Network error: {str(e)}"
        }
    except Exception as e:
        logger.error(f"Process {process_name} - Unexpected error processing {search_result.href}: {str(e)}")
        return {
            "title": search_result.title,
            "url": search_result.href,
            "abstract": search_result.abstract,
            "summary": f"Processing error: {str(e)}"
        }

def setup_logger():
    """Setup logging for each process"""
    logger = logging.getLogger("process_logger")
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - Process:%(processName)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        # Prevent propagation to avoid duplicate logs
        logger.propagate = False
    return logger

def process_in_process(user_question: str, search_result: SearchResult):
    """Function that runs in separate process"""

    # logger = setup_logger()
    # logger.info(f"Starting new process for URL: {search_result.href}")

    # Need to create new event loop for each process
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Run the async function in the process's event loop
        result = loop.run_until_complete(
            process_single_result_async(user_question, search_result)
        )
        return result
    finally:
        loop.close()

@monitor_async
async def process_search_results(question: str, search_results: list[SearchResult]):
    """Process multiple search results using true parallelism with ProcessPoolExecutor"""

    # Initialize multiprocessing logger
    mp_logger = multiprocessing.log_to_stderr()
    mp_logger.setLevel(logging.INFO)

    # Get the number of CPU cores for parallel processing
    num_processes = min(multiprocessing.cpu_count(), len(search_results))
    logger = setup_logger()
    logger.info(f"Starting processing with {num_processes} processes")

    # Create partial function with fixed question parameter
    process_func = partial(process_in_process, question)
    
    results = []
    
    # Use ProcessPoolExecutor for true parallelism
    with ProcessPoolExecutor(
        max_workers=num_processes,
        mp_context=multiprocessing.get_context('spawn')
    ) as executor:
        # Submit all tasks
        future_to_result = {
            executor.submit(process_func, result): result 
            for result in search_results
        }
        
        # Process results as they complete
        for future in concurrent.futures.as_completed(future_to_result):
            search_result = future_to_result[future]
            try:
                result = future.result()
                results.append(result)
                logger.info(f"Completed processing URL: {search_result.href}")
                # Print result as soon as it's available
                cprint(f"\nProcessed Result:", "green")
                cprint(f"Title: {result['title']}", "green")
                cprint(f"URL: {result['url']}", "green")
                cprint(f"Summary: {result['summary']}", "green")
                cprint("-" * 80, "cyan")
            except Exception as e:
                print(f"Error processing {search_result.href}: {str(e)}")
    
    return results

@Agent.tool(web_browsing)
async def web_suff(query: str):
    search_results = await web_browser(query)

    links = critic_model.generate_content(
        contents=f"{search_results}\n\nBased on the search results, which links are most relevant to the question: '{query}'?\n\n",
    )

    if isinstance(eval(links.text), List):

        # Process results in parallel
        summaries = await process_search_results(query, search_results)
    
        print(type("\n\n".join(summaries)))
        return
    else:
        return links.text


if __name__ == "__main__":
    # Set up multiprocessing logging
    pass
