
import json
import uuid
import os
import main
import logging
import random
import asyncio
import requests
import boto3
import aioboto3
import aiohttp
import xml.etree.ElementTree as ET
import concurrent.futures
import multiprocessing

from datetime import date, datetime, timedelta
from bedrock_llm import Agent
from bedrock_llm.schema import ToolMetadata, InputSchema, PropertyAttr
from bedrock_llm.monitor import monitor_async
from vnstock3 import Vnstock
from ogoogles import OGoogleS, SearchResult
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from termcolor import cprint
from botocore.exceptions import ClientError
from utils import render_template

from dotenv import load_dotenv
from bedrock_llm import AsyncClient, ModelConfig, ModelName
from bedrock_llm.schema import MessageBlock
import google.generativeai as genai
from typing import List


# Load environemnt variables
load_dotenv()
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))


hrKbID = os.environ.get("HR_KNOWLEDEG_BASE_ID")
officeKbID = os.environ.get("365OFFICE_KNOWLEDEG_BASE_ID")
summary_m_region = os.environ.get("SUMMARY_MODEL_REGION")

vnstock = Vnstock()
searcher = OGoogleS()
runtime = boto3.client("bedrock-agent-runtime", region_name=os.environ.get("KNOWLEDGE_BASE_REGION"))
gemini_models = genai.GenerativeModel("gemini-1.5-flash-002")


config = ModelConfig(
    temperature=os.environ.get("SUMMARY_MODEL_TEMP"),
    top_p=os.environ.get("SUMMARY_MODEL_TOP_P"),
    top_k=os.environ.get("SUMMARY_MODEL_TOP_K"),
    max_tokens=os.environ.get("SUMMARY_MODEL_MAXTK")
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


tool_retrieve_office365_document = ToolMetadata(
    name="retrieve_office365_document",
    description="Use this tool to retrieve information on Office365 documents.",
    input_schema=InputSchema(
        type="object",
        properties={
            "query": PropertyAttr(
                type="string",
                description="The query to retrieve the Office365 document.",
            ),
        },
        required=["query"],
    ),
)


tool_web_suffing = ToolMetadata(
    name="web_suffing",
    description="""Use this tool to browse the web and retrieve information from internet.
This tool is useful when you need to look up recent information that might not be included in the knowledge base. Use this tool for any search information on the internet that you need.""",
    input_schema=InputSchema(
        type="object",
        properties={
            "queries": PropertyAttr(
                type="array",
                description="The array of all possible questions to search the web.",
            ),
        },
        required=["queries"],
    ),
)


tool_send_email = ToolMetadata(
    name="send_email",
    description="Use this tool to send an email to a specific recipient.",
    input_schema=InputSchema(
        type="object",
        properties={
            "recipient": PropertyAttr(
                type="string",
                description="The email address of the recipient.",
            ),
            "subject": PropertyAttr(
                type="string",
                description="The subject of the email.",
            ),
            "body": PropertyAttr(
                type="string",
                description="The body of the email.",
            ),
        },
        required=["recipient", "subject", "body"],
    ),
)


tool_it_support = ToolMetadata(
    name="raise_problems_to_IT",
    description="Use this tool to send ticket to the IT support team when users encounter technical issues or problems. The tool creates a ticket in the system with a unique ID and tracks the issue.",
    input_schema=InputSchema(
        type="object",
        properties={
            "problem": PropertyAttr(
                type="string",
                description="A detailed description of the technical issue or problem being reported.",
            ),
            "sender_name": PropertyAttr(
                type="string", 
                description="The full name of the person reporting the issue.",
            ),
            "sender_role": PropertyAttr(
                type="string",
                description="The job role or position of the person reporting the issue.",
            ),
            "sender_email": PropertyAttr(
                type="string",
                description="The email address of the person reporting the issue.",
            ),
        },
        required=["problem", "sender_name", "sender_role", "sender_email"],
    ),
)


tool_update_task = ToolMetadata(
    name="update_task",
    description="Use this tool to update the status of a task in the project management system. The tool allows you to mark a task as completed, in progress, or pending.",
    input_schema=InputSchema(
        type="object",
        properties={
            "task_id": PropertyAttr(
                type="string",
                description="The unique identifier of the task to be updated.",
            ),
            "status": PropertyAttr(
                type="string",
                description="The new status of the task. It can be 'completed', 'in progress', or 'pending'.",
            ),
        },
        required=["task_id", "status"],
    ),
)


tool_create_task = ToolMetadata(
    name="create_task",
    description="Use this tool to create a new task in the project management system. The tool allows you to add a new task with a title, description, and assignee.",
    input_schema=InputSchema(
        type="object",
        properties={
            "title": PropertyAttr(
                type="string",
                description="The title of the task.",
            ),
            "description": PropertyAttr(
                type="string",
                description="The description of the task.",
            ),
            "assignee": PropertyAttr(
                type="string",
                description="The person or team assigned to the task.",
            ),
        },
        required=["title", "description", "assignee"],
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
        "knowledgeBaseId": hrKbID,  # Insert your knowledge base ID
        "retrievalConfiguration": {
            "vectorSearchConfiguration": {"numberOfResults": 25}
        },
        "retrievalQuery": {"text": query},
    }

    # Run boto3 call in a thread pool since it's blocking
    result = runtime.retrieve(**kwargs)
    return build_context_kb_prompt(result)

@Agent.tool(tool_retrieve_office365_document)
async def retrieve_office365_documentd(query: str):
    kwargs = {
        "knowledgeBaseId": officeKbID,  # Insert your knowledge base ID
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

async def web_browser(queries: List[str]):
    async def search_single_query(query: str):
        return await searcher.search(
            query=query,
            max_results=5,
            extract_text=False,
            max_text_length=200
        )

    search_tasks = [search_single_query(query) for query in queries]
    results = await asyncio.gather(*search_tasks)
    
    # Flatten results and remove duplicates based on href
    seen_hrefs = set()
    unique_results = []
    
    for result_list in results:
        for result in result_list:
            if result.href not in seen_hrefs:
                seen_hrefs.add(result.href)
                unique_results.append(result)
                
    return unique_results

async def init_bedrock_client():
    client = AsyncClient(
        region_name=summary_m_region,
        model_name=ModelName.CLAUDE_3_HAIKU
    )
    await client._get_async_client()  # Initialize the async client
    return client

async def process_single_result_async(keywords: List[str], question: str, link_browswer: str):
    logger = setup_logger()
    process_name = multiprocessing.current_process().name
    # logger.info(f"Process {process_name} starting to process URL: {search_result.href}")

    """Async part of processing a single result"""
    buffer = ""
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                link_browswer,
                timeout=aiohttp.ClientTimeout(
                    total=10,
                    connect=10/2,
                    sock_read=10/2
                )
            ) as response:
                if response.status != 200:
                    logger.error(f"Process {process_name} - Failed to fetch URL: {link_browswer} - Status: {response.status}")
                    return {
                        "url": link_browswer,
                        "summary": f"Error: Could not fetch content (Status {response.status})"
                    }
                buffer = await response.text(errors='ignore')

                # Initialize the Bedrock client
                try:
                    summary_model = await init_bedrock_client()
                except Exception as e:
                    logger.error(f"Process {process_name} - Failed to initialize Bedrock client: {str(e)}")
                    return {
                        "url": link_browswer,
                        "summary": f"AWS Client Error: {str(e)}"
                    }
                
                try:
                    async for _,_,response in summary_model.generate_async(
                        prompt=render_template(
                            "extractor.j2",{
                                "keywords": ", ".join(keywords),
                                "buffer": buffer[:100000],
                                "questions": question
                            }
                        ),
                        config=config
                    ):
                        pass

                    return {
                        "url": link_browswer,
                        "summary": response.content[0].text
                    }
                finally:
                    await summary_model.close()  # Ensure client is closed

    except aiohttp.ClientError as e:
        logger.error(f"Process {process_name} - Network error for {link_browswer}: {str(e)}")
        return {
            "url": link_browswer,
            "summary": f"Network error: {str(e)}"
        }
    except Exception as e:
        logger.error(f"Process {process_name} - Unexpected error processing {link_browswer}: {str(e)}")
        return {   
            "url": link_browswer,
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

def process_in_process(keywords: List[str], question: str, search_results: str):
    """Function that runs in separate process"""

    # logger = setup_logger()
    # logger.info(f"Starting new process for URL: {search_result.href}")

    # Need to create new event loop for each process
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Run the async function in the process's event loop
        result = loop.run_until_complete(
            process_single_result_async(keywords, question, search_results)
        )
        return result
    finally:
        loop.close()

@monitor_async
async def process_search_results(keywords: List[str], search_results: List[str], question: str):
    """Process multiple search results using true parallelism with ProcessPoolExecutor"""

    # Initialize multiprocessing logger
    mp_logger = multiprocessing.log_to_stderr()
    mp_logger.setLevel(logging.INFO)

    # Get the number of CPU cores for parallel processing
    num_processes = min(multiprocessing.cpu_count(), len(search_results))
    logger = setup_logger()
    logger.info(f"Starting processing with {num_processes} processes")

    # Create partial function with fixed question parameter
    process_func = partial(process_in_process, keywords, question)
    
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
                logger.info(f"Completed processing URL: {search_result}")
                # Print result as soon as it's available
                cprint(f"\nProcessed Result:", "green")
                cprint(f"URL: {result['url']}", "green")
                cprint("-" * 80, "cyan")
            except Exception as e:
                print(f"Error processing {search_result}: {str(e)}")
    
    return results

@Agent.tool(tool_web_suffing)
async def web_suffing(queries: List[str]):
    logger = setup_logger()
    search_results = await web_browser(queries)

    logger.info(f"Search results: {search_results}")

    evaluation = gemini_models.generate_content(
        contents=render_template(
            "links_evaluator.j2", {
                "real_date": (datetime.now() + timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S'),
                "query": queries,
                "search_results": search_results,
            }
        ),
    )

    eval_res = evaluation.text.strip()[7:-3].strip() if evaluation.text.strip().startswith('```') else evaluation.text.strip()

    logger.info(f"{eval_res}")

    if json.loads(eval_res).get("keywords"):
        eval_res = json.loads(eval_res)

        # Process results in parallel
        summaries = await process_search_results(
            eval_res["keywords"], 
            eval_res["links"],
            question=queries
        )
        
        # Extract and combine summaries into a single string
        formatted_summaries = []
        for summary in summaries:
            formatted_summary = f"""
<url>{summary['url']}</url>
<summary>{summary['summary']}</summary>
-------------------
"""
            formatted_summaries.append(formatted_summary)
        
        
        return "\n".join(formatted_summaries)
    else:
        return eval_res

@Agent.tool(tool_send_email)
async def send_email(recipient: str, subject: str, body: str, attachment_path: list[str] = []):
    try:
        # First authenticate
        auth_response = await main.login()
        
        # Check if we got redirected to Microsoft login
        if auth_response.status_code == 307:  # Temporary redirect
            return "Please authenticate first by visiting http://localhost:8000/send-email-tool/authentication"
            
        # Send the email using the correct endpoint
        email_data = {
            "to_email": recipient,
            "subject": subject,
            "body": body
        }
        
        # Convert to form data since the endpoint expects Form data
        form_data = {
            "to_email": recipient,
            "subject": subject,
            "body": body,
        }
        
        if attachment_path and len(attachment_path) > 0:
            form_data["attachment_path"] = attachment_path[0]  # Take first attachment if any
            
        email_response = requests.post(
            "http://localhost:8000/send-email-tool/send",
            data=form_data  # Use data instead of json for form data
        )
        
        if email_response.status_code != 200:
            return f"Failed to send email: {email_response.text}"
            
        return "Email sent successfully"
        
    except requests.exceptions.ConnectionError:
        return "Failed to connect to email service. Is the server running?"
    except Exception as e:
        return f"Unexpected error: {str(e)}"

@Agent.tool(tool_it_support)
async def raise_problems_to_IT(problem: str, sender_name: str, sender_role: str, sender_email: str):
    # Create a ticket data dictionary
    ticket_data = {
        'ticket_id': {'S': str(uuid.uuid4())},
        'timestamp': {'S': (datetime.now() + timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S')},
        'problem_description': {'S': problem},
        'sender_name': {'S': sender_name},
        'sender_role': {'S': sender_role},
        'sender_email': {'S': sender_email},
        'status': {'S': 'OPEN'}
    }

    try:
        # Create an aioboto3 session
        session = aioboto3.Session()
        
        async with session.client('dynamodb', region_name=os.environ.get('DYNAMO_DB_TICKET_TABLE_REGION', 'us-east-1')) as client:
            response = await client.put_item(
                TableName=os.environ.get("DYNAMO_DB_TICKET_TABLE_NAME"),
                Item=ticket_data
            )
            
            if response['ResponseMetadata']['HTTPStatusCode'] == 200:
                return f"""IT Support ticket created successfully. Ticket ID: {ticket_data['ticket_id']['S']}. Content: {problem}"""
            else:
                return f"Failed to create IT Support ticket in database with error {response}"
                
    except ClientError as e:
        error_msg = f"DynamoDB error: {str(e)}"
        logging.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logging.error(error_msg)
        return error_msg


if __name__ == "__main__":
    result = asyncio.run(web_suffing("What are configurations of the new Apple Chips?"))
    print(result)
    pass
