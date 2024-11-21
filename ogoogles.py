import asyncio
import logging
from bs4 import BeautifulSoup, SoupStrainer
from dataclasses import dataclass
import aiohttp
from typing import Dict, List, Optional, Union, TypedDict
from urllib.parse import quote, urlencode
import time
from contextlib import contextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@contextmanager
def timer(name):
    start = time.perf_counter()
    yield
    end = time.perf_counter()
    logger.info(f"{name} took {end - start:.2f} seconds")

@dataclass
class SearchResult:
    title: str
    href: str
    abstract: str
    index: int
    type: str
    visible_text: str = ""

class SearchOptions(TypedDict):
    region: str
    language: str
    safe: str
    time_period: Optional[str]

class OGoogleS:
    """
    Optimized class to perform Google searches and retrieve results.
    """
    def __init__(
        self,
        headers: Optional[Dict[str, str]] = None,
        proxy: Optional[str] = None,
        timeout: Optional[int] = 10,
        max_workers: int = 20,
    ):
        """
        Initialize the GoogleS object with improved connection handling.
        """
        self.proxy = proxy
        self.headers = headers or {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36"
        }
        self.headers["Referer"] = "https://www.google.com/"
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_workers = max_workers

    async def _get_url(self, url: str, params: Optional[Dict[str, str]] = None) -> str:
        """
        Makes an HTTP request and returns the response content.
        """
        try:
            async with aiohttp.ClientSession(headers=self.headers, timeout=self.timeout) as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        return await response.text()
                    raise Exception(f"HTTP {response.status}: {url}")
        except Exception as e:
            logger.error(f"Error fetching URL {url}: {e}")
            raise

    async def _extract_text_from_webpage(self, html_content: str, max_characters: Optional[int] = None) -> str:
        """
        Optimized text extraction from HTML content.
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser', parse_only=SoupStrainer('body'))
            
            for tag in soup(['script', 'style', 'header', 'footer', 'nav']):
                tag.decompose()

            text_parts = (tag.get_text(strip=True) for tag in soup.find_all(['p', 'h1', 'h2', 'h3']))
            result = ' '.join(text_parts)
            return result[:max_characters] if max_characters else result
        except Exception as e:
            logger.error(f"Error extracting text: {e}")
            return ""

    async def _process_search_page(self, query: str, start: int, search_params: Dict[str, str]) -> List[SearchResult]:
        """
        Process a single search results page.
        """
        try:
            url = "https://www.google.com/search"
            content = await self._get_url(url, params=search_params)
            soup = BeautifulSoup(content, 'html.parser')
            results = []
            
            for result_block in soup.find_all("div", class_="g"):
                link = result_block.find("a", href=True)
                title = result_block.find("h3")
                description_box = result_block.find("div", {"style": "-webkit-line-clamp:2"})
                
                if link and title and description_box:
                    results.append(SearchResult(
                        title=title.text,
                        href=link["href"],
                        abstract=description_box.text,
                        index=len(results) + start,
                        type="web"
                    ))
            
            return results
        except Exception as e:
            logger.error(f"Error processing search page: {e}")
            return []

    async def search(
        self,
        query: str,
        region: str = "us-en",
        language: str = "en",
        safe: str = "off",
        time_period: Optional[str] = None,
        max_results: int = 10,
        extract_text: bool = False,
        max_text_length: Optional[int] = 100,
    ) -> List[SearchResult]:
        """
        Performs an optimized Google search with parallel processing.
        """
        with timer("Search operation"):
            try:
                results = []
                tasks = []
                
                for start in range(0, max_results, 10):
                    params = {
                        "q": query,
                        "num": min(10, max_results - start),
                        "hl": language,
                        "start": start,
                        "safe": safe,
                        "gl": region,
                    }
                    if time_period:
                        params["tbs"] = f"qdr:{time_period}"
                    
                    tasks.append(self._process_search_page(query, start, params))
                
                # Gather all search results
                search_results = await asyncio.gather(*tasks)
                results = [item for sublist in search_results for item in sublist][:max_results]
                
                # Extract text if requested
                if extract_text and results:
                    text_tasks = []
                    for result in results:
                        text_tasks.append(self._extract_text_from_webpage(
                            await self._get_url(result.href),
                            max_characters=max_text_length
                        ))
                    
                    texts = await asyncio.gather(*text_tasks)
                    for result, text in zip(results, texts):
                        result.visible_text = text
                
                return results

            except Exception as e:
                logger.error(f"Search error: {e}")
                return []

async def main():
    searcher = OGoogleS()
    results = await searcher.search(
        "New relaease from Anthropic?",
        max_results=20,
        extract_text=False,
        max_text_length=200
    )
    for result in results:
        print(result)

if __name__ == "__main__":
    asyncio.run(main())