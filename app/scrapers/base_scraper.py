"""
Abstract base scraper with common HTTP client functionality
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import asyncio
import random
import httpx
from datetime import datetime
from app.models import Complaint, Error
from app.logging_config import logger
from app.config import settings


class BaseScraper(ABC):
    """Abstract base class for all scrapers with common functionality"""
    
    def __init__(self, source_name: str):
        """
        Initialize base scraper
        
        Args:
            source_name: Name of the source (e.g., 'reddit', 'google_play')
        """
        self.source_name = source_name
        self.max_retries = settings.max_retries
        self.timeout = settings.request_timeout
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        ]
        self.failed_urls: List[Dict[str, Any]] = []
        logger.info(f"{source_name} scraper initialized")
    
    @abstractmethod
    async def scrape(self) -> List[Dict[str, Any]]:
        """
        Main scraping method to be implemented by subclasses
        
        Returns:
            List of complaint data dictionaries
        """
        pass
    
    @abstractmethod
    def _parse_response(self, response: httpx.Response, url: str) -> List[Dict[str, Any]]:
        """
        Parse HTTP response to extract complaint data
        
        Args:
            response: HTTP response object
            url: URL that was scraped
            
        Returns:
            List of parsed complaint data
        """
        pass
    
    async def _retry_request(
        self, 
        url: str, 
        method: str = "GET",
        **kwargs
    ) -> Optional[httpx.Response]:
        """
        Make HTTP request with exponential backoff retry logic
        
        Args:
            url: URL to request
            method: HTTP method (default: GET)
            **kwargs: Additional arguments for httpx request
            
        Returns:
            HTTP response or None if all retries failed
        """
        retry_count = 0
        backoff_base = 1
        
        while retry_count < self.max_retries:
            try:
                # Random user agent for each request
                headers = kwargs.get('headers', {})
                headers['User-Agent'] = random.choice(self.user_agents)
                kwargs['headers'] = headers
                
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.request(method, url, **kwargs)
                    
                    # Check for rate limiting
                    if response.status_code == 429:
                        self._handle_rate_limit(response)
                        retry_count += 1
                        continue
                    
                    response.raise_for_status()
                    logger.debug(f"Successfully fetched {url} on attempt {retry_count + 1}")
                    return response
                    
            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500:
                    # Server error, retry
                    logger.warning(f"Server error {e.response.status_code} for {url}, retrying...")
                else:
                    # Client error, don't retry
                    logger.error(f"Client error {e.response.status_code} for {url}")
                    self._record_failed_url(url, str(e), "HTTPStatusError")
                    return None
                    
            except httpx.TimeoutException as e:
                logger.warning(f"Timeout for {url}, retrying...")
                
            except Exception as e:
                logger.error(f"Unexpected error for {url}: {str(e)}")
                self._record_failed_url(url, str(e), type(e).__name__)
                return None
            
            # Exponential backoff with jitter
            retry_count += 1
            if retry_count < self.max_retries:
                wait_time = backoff_base * (2 ** (retry_count - 1)) + random.uniform(0, 1)
                logger.debug(f"Waiting {wait_time:.2f} seconds before retry {retry_count}")
                await asyncio.sleep(wait_time)
        
        logger.error(f"Max retries exceeded for {url}")
        self._record_failed_url(url, "Max retries exceeded", "MaxRetriesError")
        return None
    
    def _handle_rate_limit(self, response: httpx.Response):
        """
        Handle rate limit response
        
        Args:
            response: HTTP response with 429 status
        """
        retry_after = response.headers.get('Retry-After')
        if retry_after:
            try:
                wait_time = int(retry_after)
                logger.info(f"Rate limited, waiting {wait_time} seconds as requested")
                asyncio.sleep(wait_time)
            except ValueError:
                # Retry-After might be a date, default wait
                logger.info("Rate limited, waiting 60 seconds")
                asyncio.sleep(60)
        else:
            # Default rate limit wait
            logger.info("Rate limited, waiting 30 seconds")
            asyncio.sleep(30)
    
    def _record_failed_url(self, url: str, error_message: str, error_type: str):
        """
        Record failed URL for later storage in database
        
        Args:
            url: Failed URL
            error_message: Error message
            error_type: Type of error
        """
        self.failed_urls.append({
            'source': self.source_name,
            'url': url,
            'error_message': error_message,
            'error_type': error_type,
            'occurred_at': datetime.utcnow()
        })
        logger.error(f"Recorded failed URL: {url} - {error_type}: {error_message}")
    
    def get_failed_urls(self) -> List[Error]:
        """
        Get list of Error objects for failed URLs
        
        Returns:
            List of Error model instances
        """
        errors = []
        for failed in self.failed_urls:
            errors.append(Error(
                source=failed['source'],
                url=failed['url'],
                error_message=failed['error_message'],
                error_type=failed['error_type'],
                occurred_at=failed['occurred_at']
            ))
        return errors
    
    async def fetch_multiple_urls(self, urls: List[str]) -> List[Dict[str, Any]]:
        """
        Fetch multiple URLs concurrently
        
        Args:
            urls: List of URLs to fetch
            
        Returns:
            Combined list of complaint data from all URLs
        """
        tasks = []
        for url in urls:
            task = self._fetch_and_parse(url)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_complaints = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Error in concurrent fetch: {str(result)}")
            elif result:
                all_complaints.extend(result)
        
        return all_complaints
    
    async def _fetch_and_parse(self, url: str) -> List[Dict[str, Any]]:
        """
        Fetch a URL and parse the response
        
        Args:
            url: URL to fetch
            
        Returns:
            List of parsed complaint data
        """
        response = await self._retry_request(url)
        if response:
            try:
                return self._parse_response(response, url)
            except Exception as e:
                logger.error(f"Error parsing response from {url}: {str(e)}")
                self._record_failed_url(url, f"Parse error: {str(e)}", "ParseError")
                return []
        return []