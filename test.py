import os
import random
import asyncio
from re import M
from typing import final
import boto3
import aiohttp
import xml.etree.ElementTree as ET
import concurrent.futures
import multiprocessing
import signal


from datetime import date
from bedrock_llm import Agent
from bedrock_llm.schema import ToolMetadata, InputSchema, PropertyAttr
from bedrock_llm.monitor import monitor_async
from vnstock3 import Vnstock
from ogoogles import OGoogleS, SearchResult
from concurrent.futures import ProcessPoolExecutor
from functools import partial

from dotenv import load_dotenv
import google.generativeai as genai

import logging
logging.basicConfig(level=logging.ERROR)


print(multiprocessing.cpu_count())