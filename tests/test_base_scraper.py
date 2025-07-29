"""
Unit tests for base scraper infrastructure
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import httpx
from app.scrapers.base_scraper import BaseScraper


class ConcreteScraperForTesting(BaseScraper):
    """Concrete implementation of BaseScraper for testing"""
    
    async def scrape(self):
        """Test implementation of scrape method"""
        return [{"content": "Test complaint", "source": self.source_name}]
    
    def _parse_response(self, response, url):
        """Test implementation of parse method"""
        return [{"content": response.text, "url": url}]


class TestBaseScraper:
    """Test base scraper functionality"""
    
    @pytest.fixture
    def scraper(self):
        """Create test scraper instance"""
        return ConcreteScraperForTesting("test_source")
    
    @pytest.mark.asyncio
    async def test_retry_request_success(self, scraper):
        """Test successful request on first attempt"""
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_async_client = AsyncMock()
            mock_async_client.request.return_value = mock_response
            mock_async_client.__aenter__.return_value = mock_async_client
            mock_client.return_value = mock_async_client
            
            result = await scraper._retry_request("http://test.com")
            
            assert result == mock_response
            assert mock_async_client.request.call_count == 1
    
    @pytest.mark.asyncio
    async def test_retry_request_with_retries(self, scraper):
        """Test request with retries on timeout"""
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_async_client = AsyncMock()
            # First two attempts timeout, third succeeds
            mock_async_client.request.side_effect = [
                httpx.TimeoutException("Timeout"),
                httpx.TimeoutException("Timeout"),
                mock_response
            ]
            mock_async_client.__aenter__.return_value = mock_async_client
            mock_client.return_value = mock_async_client
            
            with patch('asyncio.sleep'):  # Mock sleep to speed up test
                result = await scraper._retry_request("http://test.com")
            
            assert result == mock_response
            assert mock_async_client.request.call_count == 3
    
    @pytest.mark.asyncio
    async def test_retry_request_max_retries_exceeded(self, scraper):
        """Test request fails after max retries"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_async_client = AsyncMock()
            mock_async_client.request.side_effect = httpx.TimeoutException("Timeout")
            mock_async_client.__aenter__.return_value = mock_async_client
            mock_client.return_value = mock_async_client
            
            with patch('asyncio.sleep'):
                result = await scraper._retry_request("http://test.com")
            
            assert result is None
            assert len(scraper.failed_urls) == 1
            assert scraper.failed_urls[0]['error_type'] == "MaxRetriesError"
    
    @pytest.mark.asyncio
    async def test_retry_request_rate_limit(self, scraper):
        """Test handling rate limit (429) response"""
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 429
        mock_response.headers = {'Retry-After': '5'}
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_async_client = AsyncMock()
            mock_async_client.request.side_effect = [
                mock_response,  # First attempt rate limited
                Mock(status_code=200, raise_for_status=Mock())  # Second attempt succeeds
            ]
            mock_async_client.__aenter__.return_value = mock_async_client
            mock_client.return_value = mock_async_client
            
            with patch('asyncio.sleep') as mock_sleep:
                result = await scraper._retry_request("http://test.com")
            
            assert result is not None
            assert result.status_code == 200
    
    @pytest.mark.asyncio
    async def test_retry_request_client_error(self, scraper):
        """Test client error (4xx) doesn't retry"""
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=Mock(), response=mock_response
        )
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_async_client = AsyncMock()
            mock_async_client.request.return_value = mock_response
            mock_async_client.__aenter__.return_value = mock_async_client
            mock_client.return_value = mock_async_client
            
            result = await scraper._retry_request("http://test.com")
            
            assert result is None
            assert mock_async_client.request.call_count == 1  # No retries
            assert len(scraper.failed_urls) == 1
    
    @pytest.mark.asyncio
    async def test_retry_request_server_error(self, scraper):
        """Test server error (5xx) triggers retry"""
        mock_response_500 = Mock(spec=httpx.Response)
        mock_response_500.status_code = 500
        mock_response_500.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error", request=Mock(), response=mock_response_500
        )
        
        mock_response_200 = Mock(spec=httpx.Response)
        mock_response_200.status_code = 200
        mock_response_200.raise_for_status = Mock()
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_async_client = AsyncMock()
            mock_async_client.request.side_effect = [
                mock_response_500,  # First attempt server error
                mock_response_200   # Second attempt succeeds
            ]
            mock_async_client.__aenter__.return_value = mock_async_client
            mock_client.return_value = mock_async_client
            
            with patch('asyncio.sleep'):
                result = await scraper._retry_request("http://test.com")
            
            assert result == mock_response_200
            assert mock_async_client.request.call_count == 2
    
    def test_record_failed_url(self, scraper):
        """Test recording failed URLs"""
        scraper._record_failed_url("http://test.com", "Test error", "TestError")
        
        assert len(scraper.failed_urls) == 1
        assert scraper.failed_urls[0]['url'] == "http://test.com"
        assert scraper.failed_urls[0]['error_message'] == "Test error"
        assert scraper.failed_urls[0]['error_type'] == "TestError"
        assert scraper.failed_urls[0]['source'] == "test_source"
    
    def test_get_failed_urls(self, scraper):
        """Test getting Error objects for failed URLs"""
        scraper._record_failed_url("http://test1.com", "Error 1", "Type1")
        scraper._record_failed_url("http://test2.com", "Error 2", "Type2")
        
        errors = scraper.get_failed_urls()
        
        assert len(errors) == 2
        assert errors[0].url == "http://test1.com"
        assert errors[1].url == "http://test2.com"
        assert errors[0].source == "test_source"
    
    @pytest.mark.asyncio
    async def test_fetch_multiple_urls(self, scraper):
        """Test fetching multiple URLs concurrently"""
        urls = ["http://test1.com", "http://test2.com", "http://test3.com"]
        
        with patch.object(scraper, '_fetch_and_parse') as mock_fetch:
            mock_fetch.side_effect = [
                [{"content": "Complaint 1"}],
                [{"content": "Complaint 2"}],
                [{"content": "Complaint 3"}]
            ]
            
            results = await scraper.fetch_multiple_urls(urls)
            
            assert len(results) == 3
            assert results[0]["content"] == "Complaint 1"
            assert results[2]["content"] == "Complaint 3"
            assert mock_fetch.call_count == 3
    
    @pytest.mark.asyncio
    async def test_fetch_and_parse_success(self, scraper):
        """Test successful fetch and parse"""
        mock_response = Mock(spec=httpx.Response)
        mock_response.text = "Test response"
        
        with patch.object(scraper, '_retry_request') as mock_retry:
            mock_retry.return_value = mock_response
            
            results = await scraper._fetch_and_parse("http://test.com")
            
            assert len(results) == 1
            assert results[0]["content"] == "Test response"
            assert results[0]["url"] == "http://test.com"
    
    @pytest.mark.asyncio
    async def test_fetch_and_parse_parse_error(self, scraper):
        """Test parse error handling"""
        mock_response = Mock(spec=httpx.Response)
        
        with patch.object(scraper, '_retry_request') as mock_retry:
            mock_retry.return_value = mock_response
            
            with patch.object(scraper, '_parse_response') as mock_parse:
                mock_parse.side_effect = Exception("Parse error")
                
                results = await scraper._fetch_and_parse("http://test.com")
                
                assert len(results) == 0
                assert len(scraper.failed_urls) == 1
                assert "Parse error" in scraper.failed_urls[0]['error_message']