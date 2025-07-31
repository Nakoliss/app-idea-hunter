"""
Reddit scraper implementation for collecting complaints from subreddits
"""
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import httpx
from app.scrapers.base_scraper import BaseScraper
from app.logging_config import logger


class RedditScraper(BaseScraper):
    """Scraper for Reddit posts and comments"""
    
    def __init__(self, subreddits: Optional[List[str]] = None):
        """
        Initialize Reddit scraper
        
        Args:
            subreddits: List of subreddit names to scrape
        """
        super().__init__("reddit")
        self.subreddits = subreddits or [
            "technology",
            "apps",
            "androidapps",
            "iosapps",
            "mobileapps",
            "SomebodyMakeThis",
            "AppIdeas",
            "Startup_Ideas",
            "feature_requests",
            "Entrepreneur",
            "SideProject",
            "indiebiz",
            "smallbusiness",
            "startups"
        ]
        self.base_url = "https://www.reddit.com"
        self.posts_per_subreddit = 100
        logger.info("Reddit Scraper initialized with expanded subreddits for app ideas and complaints.")
        
    async def scrape(self) -> List[Dict[str, Any]]:
        """
        Scrape complaints from configured subreddits
        
        Returns:
            List of complaint data dictionaries
        """
        all_complaints = []
        
        for subreddit in self.subreddits:
            logger.info(f"Scraping subreddit: r/{subreddit}")
            
            # Get hot posts
            hot_url = f"{self.base_url}/r/{subreddit}/hot.json?limit={self.posts_per_subreddit}"
            hot_complaints = await self._fetch_and_parse(hot_url)
            all_complaints.extend(hot_complaints)
            
            # Get new posts
            new_url = f"{self.base_url}/r/{subreddit}/new.json?limit={self.posts_per_subreddit}"
            new_complaints = await self._fetch_and_parse(new_url)
            all_complaints.extend(new_complaints)
            
            logger.info(f"Collected {len(hot_complaints) + len(new_complaints)} items from r/{subreddit}")
        
        # Also fetch comments from posts
        for complaint in all_complaints[:50]:  # Limit to avoid too many requests
            if complaint.get('metadata', {}).get('post_id'):
                comments = await self._fetch_post_comments(
                    complaint['metadata']['subreddit'],
                    complaint['metadata']['post_id']
                )
                all_complaints.extend(comments)
        
        logger.info(f"Total Reddit complaints collected: {len(all_complaints)}")
        return all_complaints
    
    def _parse_response(self, response: httpx.Response, url: str) -> List[Dict[str, Any]]:
        """
        Parse Reddit JSON response
        
        Args:
            response: HTTP response from Reddit
            url: URL that was scraped
            
        Returns:
            List of parsed complaint data
        """
        complaints = []
        
        try:
            data = response.json()
            
            if 'data' not in data or 'children' not in data['data']:
                logger.warning(f"Unexpected Reddit response structure from {url}")
                return complaints
            
            for item in data['data']['children']:
                post_data = item['data']
                
                # Extract post content
                if item['kind'] == 't3':  # Post
                    content = self._extract_post_content(post_data)
                    if content:
                        complaints.append({
                            'content': content,
                            'source': self.source_name,
                            'source_url': f"{self.base_url}{post_data.get('permalink', '')}",
                            'metadata': {
                                'subreddit': post_data.get('subreddit', ''),
                                'author': post_data.get('author', ''),
                                'post_id': post_data.get('id', ''),
                                'score': post_data.get('score', 0),
                                'created_utc': post_data.get('created_utc', 0),
                                'type': 'post'
                            }
                        })
                
                elif item['kind'] == 't1':  # Comment
                    content = post_data.get('body', '').strip()
                    if content and content != '[deleted]' and content != '[removed]':
                        complaints.append({
                            'content': content,
                            'source': self.source_name,
                            'source_url': f"{self.base_url}{post_data.get('permalink', '')}",
                            'metadata': {
                                'subreddit': post_data.get('subreddit', ''),
                                'author': post_data.get('author', ''),
                                'post_id': post_data.get('link_id', '').replace('t3_', ''),
                                'comment_id': post_data.get('id', ''),
                                'score': post_data.get('score', 0),
                                'created_utc': post_data.get('created_utc', 0),
                                'type': 'comment'
                            }
                        })
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from {url}: {str(e)}")
        except Exception as e:
            logger.error(f"Error parsing Reddit response from {url}: {str(e)}")
        
        return complaints
    
    def _extract_post_content(self, post_data: Dict[str, Any]) -> Optional[str]:
        """
        Extract content from Reddit post data
        
        Args:
            post_data: Reddit post data dictionary
            
        Returns:
            Post content or None if not suitable
        """
        # Skip posts that are likely not complaints
        if post_data.get('is_video') or post_data.get('is_gallery'):
            return None
        
        # Combine title and selftext
        title = post_data.get('title', '').strip()
        selftext = post_data.get('selftext', '').strip()
        
        # Skip deleted/removed posts
        if title in ['[deleted]', '[removed]'] or selftext in ['[deleted]', '[removed]']:
            return None
        
        # Combine title and body
        content = title
        if selftext and selftext not in ['', '[deleted]', '[removed]']:
            content = f"{title}\n\n{selftext}"
        
        # Skip very short posts that are likely not complaints
        if len(content) < 20:
            return None
        
        return content
    
    async def _fetch_post_comments(self, subreddit: str, post_id: str) -> List[Dict[str, Any]]:
        """
        Fetch comments from a specific post
        
        Args:
            subreddit: Subreddit name
            post_id: Post ID
            
        Returns:
            List of comment complaints
        """
        url = f"{self.base_url}/r/{subreddit}/comments/{post_id}.json?limit=100"
        
        response = await self._retry_request(url)
        if not response:
            return []
        
        complaints = []
        
        try:
            data = response.json()
            
            # Comments are in the second element
            if len(data) > 1 and isinstance(data[1], dict):
                comments_data = data[1]
                if 'data' in comments_data and 'children' in comments_data['data']:
                    for item in comments_data['data']['children']:
                        if item['kind'] == 't1':  # Comment
                            comment_data = item['data']
                            content = comment_data.get('body', '').strip()
                            
                            if content and content not in ['[deleted]', '[removed]'] and len(content) > 20:
                                complaints.append({
                                    'content': content,
                                    'source': self.source_name,
                                    'source_url': f"{self.base_url}{comment_data.get('permalink', '')}",
                                    'metadata': {
                                        'subreddit': subreddit,
                                        'author': comment_data.get('author', ''),
                                        'post_id': post_id,
                                        'comment_id': comment_data.get('id', ''),
                                        'score': comment_data.get('score', 0),
                                        'created_utc': comment_data.get('created_utc', 0),
                                        'type': 'comment'
                                    }
                                })
        
        except Exception as e:
            logger.error(f"Error parsing comments for post {post_id}: {str(e)}")
        
        return complaints
    
    async def scrape_search_results(self, query: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Scrape Reddit search results for specific queries
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of complaint data from search results
        """
        search_url = f"{self.base_url}/search.json?q={query}&sort=new&limit={limit}"
        return await self._fetch_and_parse(search_url)