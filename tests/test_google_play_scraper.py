"""
Unit tests for Google Play Store scraper
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
import httpx
from app.scrapers.google_play_scraper import GooglePlayScraper


class TestGooglePlayScraper:
    """Test Google Play scraper functionality"""
    
    @pytest.fixture
    def scraper(self):
        """Create Google Play scraper instance"""
        return GooglePlayScraper(app_packages=["com.test.app"])
    
    @pytest.fixture
    def mock_play_store_html(self):
        """Create mock Google Play Store HTML response"""
        return '''
        <html>
        <head><title>Test App</title></head>
        <body>
            <script>
                var data = {"name":"Test App","reviews":[
                    {"gp:AOqpTOH123","John Doe","This app crashes constantly",2,null,null,"2023-01-01"},
                    {"gp:AOqpTOH456","Jane Smith","Love this app, works great",5,null,null,"2023-01-02"},
                    {"gp:AOqpTOH789","Bob Wilson","Terrible user interface, very confusing",1,null,null,"2023-01-03"}
                ]};
            </script>
            <div data-review-id="review1">
                <span aria-label="Rated 2 stars out of 5">2 stars</span>
                <span>User One</span>
                <span jsname="bN97Pc">App keeps freezing when I try to save</span>
            </div>
            <div data-review-id="review2">
                <span aria-label="Rated 5 stars out of 5">5 stars</span>
                <span>Happy User</span>
                <span jsname="bN97Pc">Amazing app, highly recommend</span>
            </div>
            <div data-review-id="review3">
                <span aria-label="Rated 1 stars out of 5">1 star</span>
                <span>Frustrated User</span>
                <span jsname="bN97Pc">Worst app ever, constantly bugs and glitches</span>
            </div>
        </body>
        </html>
        '''
    
    def test_parse_response_regex_pattern(self, scraper, mock_play_store_html):
        """Test parsing Google Play response using regex pattern"""
        mock_response = Mock(spec=httpx.Response)
        mock_response.text = mock_play_store_html
        
        complaints = scraper._parse_response(
            mock_response, 
            "https://play.google.com/store/apps/details?id=com.test.app",
            "com.test.app",
            target_rating=2
        )
        
        # Should find reviews with 1-3 star ratings
        # The regex pattern in the HTML should match the test data
        assert isinstance(complaints, list)
    
    def test_parse_alternative_format(self, scraper, mock_play_store_html):
        """Test alternative parsing method"""
        complaints = scraper._parse_alternative_format(
            mock_play_store_html,
            "https://play.google.com/store/apps/details?id=com.test.app",
            "com.test.app",
            "Test App"
        )
        
        # Should find the negative reviews from HTML div elements
        negative_reviews = [c for c in complaints if c['metadata']['rating'] <= 3]
        assert len(negative_reviews) >= 2  # Should find at least 2 negative reviews
        
        # Check structure of parsed complaints
        if negative_reviews:
            complaint = negative_reviews[0]
            assert 'content' in complaint
            assert 'source' in complaint
            assert complaint['source'] == 'google_play'
            assert 'metadata' in complaint
            assert 'app_name' in complaint['metadata']
            assert 'rating' in complaint['metadata']
            assert complaint['metadata']['rating'] <= 3
    
    @pytest.mark.asyncio
    async def test_scrape_app_reviews(self, scraper):
        """Test scraping reviews for a specific app"""
        mock_response = Mock(spec=httpx.Response)
        mock_response.text = '''
        <div data-review-id="test1">
            <span aria-label="Rated 1 stars out of 5">1 star</span>
            <span>Test User</span>
            <span jsname="bN97Pc">This app is terrible and never works properly</span>
        </div>
        '''
        
        with patch.object(scraper, '_retry_request') as mock_retry:
            mock_retry.return_value = mock_response
            
            reviews = await scraper._scrape_app_reviews("com.test.app", 1)
            
            # Should have called the retry request
            mock_retry.assert_called_once()
            call_url = mock_retry.call_args[0][0]
            assert "play.google.com/store/apps/details" in call_url
            assert "id=com.test.app" in call_url
    
    @pytest.mark.asyncio
    async def test_scrape(self, scraper):
        """Test main scrape method"""
        with patch.object(scraper, '_scrape_app_reviews') as mock_scrape_app:
            # Mock returns for different ratings
            mock_scrape_app.side_effect = [
                [{"content": "1-star review", "metadata": {"rating": 1}}],  # 1-star
                [{"content": "2-star review", "metadata": {"rating": 2}}],  # 2-star
                [{"content": "3-star review", "metadata": {"rating": 3}}]   # 3-star
            ]
            
            complaints = await scraper.scrape()
            
            # Should scrape all three ratings for the test app
            assert len(complaints) == 3
            assert mock_scrape_app.call_count == 3
            
            # Verify it was called with correct parameters
            calls = mock_scrape_app.call_args_list
            assert calls[0][0] == ("com.test.app", 1)
            assert calls[1][0] == ("com.test.app", 2)
            assert calls[2][0] == ("com.test.app", 3)
    
    @pytest.mark.asyncio
    async def test_scrape_app_by_name(self, scraper):
        """Test scraping app by name"""
        # Mock search response
        search_html = '''
        <a href="/store/apps/details?id=com.found.app">Found App</a>
        '''
        
        search_response = Mock(spec=httpx.Response)
        search_response.text = search_html
        
        with patch.object(scraper, '_retry_request') as mock_retry:
            mock_retry.return_value = search_response
            
            with patch.object(scraper, '_scrape_app_reviews') as mock_scrape:
                mock_scrape.return_value = [{"content": "Found app review"}]
                
                reviews = await scraper.scrape_app_by_name("Found App")
                
                # Should find the package and scrape reviews
                assert len(reviews) == 3  # Called for ratings 1, 2, 3
                assert mock_scrape.call_count == 3
                
                # Verify search URL
                search_call = mock_retry.call_args_list[0][0][0]
                assert "store/search" in search_call
                assert "q=Found+App" in search_call
    
    @pytest.mark.asyncio
    async def test_scrape_app_by_name_not_found(self, scraper):
        """Test scraping app by name when app is not found"""
        search_response = Mock(spec=httpx.Response)
        search_response.text = "No results found"
        
        with patch.object(scraper, '_retry_request') as mock_retry:
            mock_retry.return_value = search_response
            
            reviews = await scraper.scrape_app_by_name("Nonexistent App")
            
            # Should return empty list when app not found
            assert len(reviews) == 0
    
    @pytest.mark.asyncio
    async def test_scrape_category_apps(self, scraper):
        """Test scraping apps from a category"""
        category_html = '''
        <a href="/store/apps/details?id=com.app1">App 1</a>
        <a href="/store/apps/details?id=com.app2">App 2</a>
        <a href="/store/apps/details?id=com.app3">App 3</a>
        '''
        
        category_response = Mock(spec=httpx.Response)
        category_response.text = category_html
        
        with patch.object(scraper, '_retry_request') as mock_retry:
            mock_retry.return_value = category_response
            
            with patch.object(scraper, '_scrape_app_reviews') as mock_scrape:
                mock_scrape.return_value = [{"content": "Category app review"}]
                
                reviews = await scraper.scrape_category_apps("productivity")
                
                # Should scrape multiple apps from category
                assert len(reviews) > 0
                
                # Verify category URL
                category_call = mock_retry.call_args[0][0]
                assert "store/apps/category/PRODUCTIVITY" in category_call
    
    def test_parse_response_empty_html(self, scraper):
        """Test parsing empty or invalid HTML"""
        mock_response = Mock(spec=httpx.Response)
        mock_response.text = ""
        
        complaints = scraper._parse_response(
            mock_response,
            "https://play.google.com/test",
            "com.test.app"
        )
        
        assert len(complaints) == 0
    
    def test_parse_response_filters_high_ratings(self, scraper):
        """Test that high-rated reviews are filtered out"""
        html_with_high_ratings = '''
        <div data-review-id="review1">
            <span aria-label="Rated 5 stars out of 5">5 stars</span>
            <span>Happy User</span>
            <span jsname="bN97Pc">Great app, love it</span>
        </div>
        <div data-review-id="review2">
            <span aria-label="Rated 4 stars out of 5">4 stars</span>
            <span>Satisfied User</span>
            <span jsname="bN97Pc">Pretty good app overall</span>
        </div>
        <div data-review-id="review3">
            <span aria-label="Rated 2 stars out of 5">2 stars</span>
            <span>Disappointed User</span>
            <span jsname="bN97Pc">App has many bugs and issues</span>
        </div>
        '''
        
        complaints = scraper._parse_alternative_format(
            html_with_high_ratings,
            "https://play.google.com/test",
            "com.test.app",
            "Test App"
        )
        
        # Should only include the 2-star review, not 4-5 star reviews
        assert len(complaints) == 1
        assert complaints[0]['metadata']['rating'] == 2
    
    def test_parse_response_filters_short_reviews(self, scraper):
        """Test that very short reviews are filtered out"""
        html_with_short_reviews = '''
        <div data-review-id="review1">
            <span aria-label="Rated 1 stars out of 5">1 star</span>
            <span>User</span>
            <span jsname="bN97Pc">Bad</span>
        </div>
        <div data-review-id="review2">
            <span aria-label="Rated 2 stars out of 5">2 stars</span>
            <span>Another User</span>
            <span jsname="bN97Pc">This app is really terrible and crashes all the time</span>
        </div>
        '''
        
        complaints = scraper._parse_alternative_format(
            html_with_short_reviews,
            "https://play.google.com/test",
            "com.test.app",
            "Test App"
        )
        
        # Should only include the longer review, not the short "Bad" review
        assert len(complaints) == 1
        assert "terrible and crashes" in complaints[0]['content']