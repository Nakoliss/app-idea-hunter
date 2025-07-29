"""
Unit tests for Reddit scraper
"""
import pytest
import json
from unittest.mock import Mock, patch, AsyncMock
import httpx
from app.scrapers.reddit_scraper import RedditScraper


class TestRedditScraper:
    """Test Reddit scraper functionality"""
    
    @pytest.fixture
    def scraper(self):
        """Create Reddit scraper instance"""
        return RedditScraper(subreddits=["test_subreddit"])
    
    @pytest.fixture
    def mock_reddit_response(self):
        """Create mock Reddit API response"""
        return {
            "data": {
                "children": [
                    {
                        "kind": "t3",
                        "data": {
                            "id": "post123",
                            "title": "This app keeps crashing every time I open it",
                            "selftext": "I've tried reinstalling but it still crashes",
                            "author": "testuser",
                            "subreddit": "test_subreddit",
                            "permalink": "/r/test_subreddit/comments/post123/",
                            "score": 42,
                            "created_utc": 1234567890,
                            "is_video": False,
                            "is_gallery": False
                        }
                    },
                    {
                        "kind": "t3",
                        "data": {
                            "id": "post456",
                            "title": "Why is this app so slow?",
                            "selftext": "",
                            "author": "anotheruser",
                            "subreddit": "test_subreddit",
                            "permalink": "/r/test_subreddit/comments/post456/",
                            "score": 15,
                            "created_utc": 1234567900,
                            "is_video": False,
                            "is_gallery": False
                        }
                    }
                ]
            }
        }
    
    @pytest.fixture
    def mock_comments_response(self):
        """Create mock Reddit comments response"""
        return [
            {},  # First element is post data
            {
                "data": {
                    "children": [
                        {
                            "kind": "t1",
                            "data": {
                                "id": "comment123",
                                "body": "I have the same problem, it crashes constantly",
                                "author": "commenter1",
                                "permalink": "/r/test_subreddit/comments/post123/comment123/",
                                "score": 10,
                                "created_utc": 1234567895
                            }
                        },
                        {
                            "kind": "t1",
                            "data": {
                                "id": "comment456",
                                "body": "[deleted]",
                                "author": "[deleted]",
                                "permalink": "/r/test_subreddit/comments/post123/comment456/",
                                "score": 0,
                                "created_utc": 1234567896
                            }
                        }
                    ]
                }
            }
        ]
    
    def test_parse_response_posts(self, scraper, mock_reddit_response):
        """Test parsing Reddit posts response"""
        mock_response = Mock(spec=httpx.Response)
        mock_response.json.return_value = mock_reddit_response
        
        complaints = scraper._parse_response(mock_response, "http://reddit.com/test")
        
        assert len(complaints) == 2
        
        # Check first post
        assert complaints[0]['content'] == "This app keeps crashing every time I open it\n\nI've tried reinstalling but it still crashes"
        assert complaints[0]['source'] == "reddit"
        assert complaints[0]['source_url'] == "https://www.reddit.com/r/test_subreddit/comments/post123/"
        assert complaints[0]['metadata']['post_id'] == "post123"
        assert complaints[0]['metadata']['author'] == "testuser"
        assert complaints[0]['metadata']['type'] == "post"
        
        # Check second post (no selftext)
        assert complaints[1]['content'] == "Why is this app so slow?"
        assert complaints[1]['metadata']['post_id'] == "post456"
    
    def test_parse_response_comments(self, scraper):
        """Test parsing Reddit comments response"""
        mock_response = Mock(spec=httpx.Response)
        mock_response.json.return_value = {
            "data": {
                "children": [
                    {
                        "kind": "t1",
                        "data": {
                            "id": "comment789",
                            "body": "The UI is terrible and confusing",
                            "author": "user123",
                            "subreddit": "test_subreddit",
                            "permalink": "/r/test_subreddit/comments/post/comment789/",
                            "link_id": "t3_post123",
                            "score": 5,
                            "created_utc": 1234567890
                        }
                    }
                ]
            }
        }
        
        complaints = scraper._parse_response(mock_response, "http://reddit.com/test")
        
        assert len(complaints) == 1
        assert complaints[0]['content'] == "The UI is terrible and confusing"
        assert complaints[0]['metadata']['type'] == "comment"
        assert complaints[0]['metadata']['comment_id'] == "comment789"
        assert complaints[0]['metadata']['post_id'] == "post123"
    
    def test_extract_post_content(self, scraper):
        """Test extracting post content"""
        # Normal post
        post_data = {
            'title': 'App crashes on startup',
            'selftext': 'Every time I try to open the app it crashes immediately',
            'is_video': False,
            'is_gallery': False
        }
        
        content = scraper._extract_post_content(post_data)
        assert content == "App crashes on startup\n\nEvery time I try to open the app it crashes immediately"
        
        # Post with no selftext
        post_data = {
            'title': 'Why is this app so buggy?',
            'selftext': '',
            'is_video': False,
            'is_gallery': False
        }
        
        content = scraper._extract_post_content(post_data)
        assert content == "Why is this app so buggy?"
        
        # Video post (should be skipped)
        post_data = {
            'title': 'Check out this video',
            'selftext': 'Video content',
            'is_video': True,
            'is_gallery': False
        }
        
        content = scraper._extract_post_content(post_data)
        assert content is None
        
        # Deleted post
        post_data = {
            'title': '[deleted]',
            'selftext': '[deleted]',
            'is_video': False,
            'is_gallery': False
        }
        
        content = scraper._extract_post_content(post_data)
        assert content is None
        
        # Very short post
        post_data = {
            'title': 'Bad',
            'selftext': '',
            'is_video': False,
            'is_gallery': False
        }
        
        content = scraper._extract_post_content(post_data)
        assert content is None
    
    @pytest.mark.asyncio
    async def test_scrape(self, scraper, mock_reddit_response):
        """Test main scrape method"""
        with patch.object(scraper, '_fetch_and_parse') as mock_fetch:
            # Mock responses for hot and new posts
            mock_fetch.side_effect = [
                [  # Hot posts
                    {
                        'content': 'Hot post complaint',
                        'source': 'reddit',
                        'metadata': {'post_id': 'hot1', 'subreddit': 'test_subreddit'}
                    }
                ],
                [  # New posts
                    {
                        'content': 'New post complaint',
                        'source': 'reddit',
                        'metadata': {'post_id': 'new1', 'subreddit': 'test_subreddit'}
                    }
                ]
            ]
            
            with patch.object(scraper, '_fetch_post_comments') as mock_comments:
                mock_comments.return_value = []
                
                complaints = await scraper.scrape()
                
                assert len(complaints) == 2
                assert complaints[0]['content'] == 'Hot post complaint'
                assert complaints[1]['content'] == 'New post complaint'
                
                # Verify URLs were called
                assert mock_fetch.call_count == 2
                hot_url = mock_fetch.call_args_list[0][0][0]
                new_url = mock_fetch.call_args_list[1][0][0]
                assert "hot.json" in hot_url
                assert "new.json" in new_url
    
    @pytest.mark.asyncio
    async def test_fetch_post_comments(self, scraper, mock_comments_response):
        """Test fetching comments from a post"""
        mock_response = Mock(spec=httpx.Response)
        mock_response.json.return_value = mock_comments_response
        
        with patch.object(scraper, '_retry_request') as mock_retry:
            mock_retry.return_value = mock_response
            
            comments = await scraper._fetch_post_comments("test_subreddit", "post123")
            
            assert len(comments) == 1  # Only one valid comment (other is deleted)
            assert comments[0]['content'] == "I have the same problem, it crashes constantly"
            assert comments[0]['metadata']['comment_id'] == "comment123"
            assert comments[0]['metadata']['type'] == "comment"
    
    @pytest.mark.asyncio
    async def test_scrape_search_results(self, scraper, mock_reddit_response):
        """Test scraping search results"""
        mock_response = Mock(spec=httpx.Response)
        mock_response.json.return_value = mock_reddit_response
        
        with patch.object(scraper, '_fetch_and_parse') as mock_fetch:
            mock_fetch.return_value = [{"content": "Search result complaint"}]
            
            results = await scraper.scrape_search_results("app crash", limit=50)
            
            assert len(results) == 1
            assert results[0]['content'] == "Search result complaint"
            
            # Verify search URL
            call_url = mock_fetch.call_args[0][0]
            assert "search.json" in call_url
            assert "q=app crash" in call_url
            assert "limit=50" in call_url
    
    def test_parse_response_invalid_json(self, scraper):
        """Test handling invalid JSON response"""
        mock_response = Mock(spec=httpx.Response)
        mock_response.json.side_effect = json.JSONDecodeError("Invalid", "", 0)
        
        complaints = scraper._parse_response(mock_response, "http://reddit.com/test")
        
        assert len(complaints) == 0
    
    def test_parse_response_unexpected_structure(self, scraper):
        """Test handling unexpected response structure"""
        mock_response = Mock(spec=httpx.Response)
        mock_response.json.return_value = {"unexpected": "structure"}
        
        complaints = scraper._parse_response(mock_response, "http://reddit.com/test")
        
        assert len(complaints) == 0