import random
import asyncio
import boto3
import xml.etree.ElementTree as ET

from datetime import date
from bedrock_llm import Agent
from bedrock_llm.schema import ToolMetadata, InputSchema, PropertyAttr
from vnstock3 import Vnstock


vnstock = Vnstock()
runtime = boto3.client("bedrock-agent-runtime", region_name="us-east-1")


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
async def knowledge_base_retrieve(query: str):
    kwargs = {
        "knowledgeBaseId": "GFBFDZFDEZ",  # Insert your knowledge base ID
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