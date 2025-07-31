"""
Google Play Store scraper for collecting 1-3 star reviews
"""
import re
import json
from typing import List, Dict, Any, Optional
from urllib.parse import quote_plus
import httpx
from app.scrapers.base_scraper import BaseScraper
from app.logging_config import logger


class GooglePlayScraper(BaseScraper):
    """Scraper for Google Play Store reviews"""
    
    def __init__(self, app_packages: Optional[List[str]] = None):
        """
        Initialize Google Play scraper
        
        Args:
            app_packages: List of app package names to scrape (if None, will scrape by categories)
        """
        super().__init__("google_play")
        self.app_packages = None  # Default to None to use category scraping
        self.base_url = "https://play.google.com"
        self.reviews_per_app = 200
        logger.info("Google Play Scraper initialized to focus on niche apps with 1-3 star ratings.")
        
        # Focus on niche apps by targeting less popular or specific category apps later in scrape_category_apps
        logger.info("Google Play Scraper initialized to focus on niche apps with 1-3 star ratings.")
        
    async def scrape(self) -> List[Dict[str, Any]]:
        """
        Scrape 1-3 star reviews from configured apps or categories for niche focus
        
        Returns:
            List of complaint data dictionaries
        """
        all_complaints = []
        
        if self.app_packages:
            for package_name in self.app_packages:
                logger.info(f"Scraping reviews for app: {package_name}")
                
                # Get reviews for different ratings
                for rating in [1, 2, 3]:
                    reviews = await self._scrape_app_reviews(package_name, rating)
                    all_complaints.extend(reviews)
                    logger.info(f"Collected {len(reviews)} {rating}-star reviews for {package_name}")
        else:
            # If no specific apps provided, scrape from categories likely to have niche apps
            categories = ["PRODUCTIVITY", "TOOLS", "LIFESTYLE", "HEALTH_AND_FITNESS"]
            for category in categories:
                logger.info(f"Scraping category: {category}")
                category_complaints = await self.scrape_category_apps(category.lower())
                all_complaints.extend(category_complaints)
                logger.info(f"Collected {len(category_complaints)} reviews from {category}")
        
        logger.info(f"Total Google Play complaints collected: {len(all_complaints)}")
        return all_complaints
    
    async def _scrape_app_reviews(
        self, 
        package_name: str, 
        rating: int,
        sort_order: str = "newest"
    ) -> List[Dict[str, Any]]:
        """
        Scrape reviews for a specific app and rating
        
        Args:
            package_name: App package name
            rating: Star rating (1-5)
            sort_order: Sort order (newest, rating, helpfulness)
            
        Returns:
            List of review complaints
        """
        # Use the reviews endpoint directly with rating filter
        reviews_url = f"{self.base_url}/store/apps/details?id={package_name}&showAllReviews=true&reviewSort=1&rating={rating}"
        response = await self._retry_request(reviews_url)
        if not response:
            return []
            
        # Extract reviews using JSON pattern
        reviews = []
        try:
            # Look for review data in script tags
            script_tags = re.findall(r'<script[^>]*>(.*?)</script>', response.text, re.DOTALL)
            for script in script_tags:
                # Look for review objects
                review_matches = re.findall(r'\{"reviewId":"[^"]+","reviewerName":"([^"]+)","content":"([^"]+)","rating":(\d+),"timestamp":"([^"]+)"', script)
                for reviewer, content, stars, timestamp in review_matches:
                    if int(stars) == rating:  # Verify rating matches
                        reviews.append({
                            "source": self.source_name,
                            "content": content.replace('\\n', '\n').replace('\\"', '"'),
                            "metadata": {
                                "package_name": package_name,
                                "rating": int(stars),
                                "review_date": timestamp,
                                "reviewer": reviewer
                            }
                        })
        except Exception as e:
            logger.error(f"Error parsing reviews for {package_name}: {str(e)}")
        
        logger.info(f"Found {len(reviews)} {rating}-star reviews for {package_name}")
        return reviews[:self.reviews_per_app]  # Limit to configured amount
    
    async def _fetch_reviews_from_page(
        self, 
        url: str, 
        package_name: str, 
        target_rating: int
    ) -> List[Dict[str, Any]]:
        """
        Fetch reviews from Google Play app page
        
        Args:
            url: App URL
            package_name: App package name
            target_rating: Target star rating to filter
            
        Returns:
            List of review complaints
        """
        response = await self._retry_request(url)
        if not response:
            return []
        
        return self._parse_response(response, url, package_name, target_rating)
    
    def _parse_response(
        self, 
        response: httpx.Response, 
        url: str,
        package_name: str = "",
        target_rating: int = None
    ) -> List[Dict[str, Any]]:
        """
        Parse Google Play response to extract reviews
        
        Args:
            response: HTTP response
            url: Request URL
            package_name: App package name
            target_rating: Target star rating to filter
            
        Returns:
            List of review complaints
        """
        complaints = []
        
        # Extract app name if available
        app_name_match = re.search(r'<title[^>]*>([^<]+) - Apps on Google Play</title>', response.text)
        app_name = app_name_match.group(1) if app_name_match else package_name
        
        # Try to find reviews in the response
        review_blocks = re.findall(r'<div class="[^"]*review-body[^"]*"[^>]*>.*?</div>', response.text, re.DOTALL)
        if not review_blocks:
            # Try alternative format
            return self._parse_alternative_format(response.text, url, package_name, app_name)
        
        for block in review_blocks:
            # Extract rating
            rating_match = re.search(r'<div class="[^"]*star-rating[^"]*"[^>]*>.*?<div class="[^"]*tiny-star[^"]*"[^>]*aria-label="[^"]*Rated (\d) star', block, re.DOTALL)
            if not rating_match:
                continue
            
            rating = int(rating_match.group(1))
            if target_rating and rating != target_rating:
                continue
            
            # Only process 1-3 star reviews
            if rating > 3:
                continue
            
            # Extract review text
            text_match = re.search(r'<span[^>]*jsname="[^"]*"[^>]*>(.*?)</span>', block, re.DOTALL)
            if not text_match:
                continue
            
            content = text_match.group(1).strip()
            if not content:
                continue
            
            # Check if the review contains ideas or feature requests
            idea_keywords = ["i wish", "would be great", "should have", "needs to", "if only", "please add", "can you add", "hope they add"]
            is_idea = any(keyword in content.lower() for keyword in idea_keywords)
            
            # Extract date if possible
            date_match = re.search(r'<span class="[^"]*review-date[^"]*"[^>]*>(.*?)</span>', block)
            date_str = date_match.group(1) if date_match else ""
            
            complaints.append({
                "source": self.source_name,
                "content": content,
                "metadata": {
                    "app_name": app_name,
                    "package_name": package_name,
                    "rating": rating,
                    "review_date": date_str,
                    "is_idea": is_idea
                }
            })
        
        return complaints
    
    def _parse_alternative_format(
        self, 
        html_content: str, 
        url: str, 
        package_name: str,
        app_name: str
    ) -> List[Dict[str, Any]]:
        """
        Alternative parsing method for Google Play reviews
        
        Args:
            html_content: HTML content to parse
            url: Source URL
            package_name: App package name
            app_name: App name
            
        Returns:
            List of review complaints
        """
        complaints = []
        
        try:
            # Look for review containers in HTML
            review_blocks = re.findall(
                r'<div[^>]*data-review-id[^>]*>.*?</div>',
                html_content,
                re.DOTALL
            )
            
            for block in review_blocks:
                # Extract rating
                rating_match = re.search(r'aria-label="Rated (\d+) stars', block)
                if not rating_match:
                    continue
                    
                rating = int(rating_match.group(1))
                if rating > 3:  # Only negative reviews
                    continue
                
                # Extract review text
                text_match = re.search(r'<span[^>]*jsname="[^"]*"[^>]*>([^<]+)</span>', block)
                if not text_match:
                    continue
                
                review_text = text_match.group(1).strip()
                if len(review_text) < 10:
                    continue
                
                # Extract reviewer name
                name_match = re.search(r'<span[^>]*>([^<]+)</span>', block)
                reviewer_name = name_match.group(1) if name_match else "Anonymous"
                
                complaints.append({
                    'content': review_text,
                    'source': self.source_name,
                    'source_url': url,
                    'metadata': {
                        'app_name': app_name,
                        'package_name': package_name,
                        'reviewer': reviewer_name,
                        'rating': rating,
                        'type': 'review'
                    }
                })
        
        except Exception as e:
            logger.debug(f"Alternative parsing failed: {str(e)}")
        
        return complaints
    
    async def scrape_app_by_name(self, app_name: str) -> List[Dict[str, Any]]:
        """
        Search for an app by name and scrape its reviews
        
        Args:
            app_name: Name of the app to search for
            
        Returns:
            List of review complaints
        """
        # Search for the app first
        search_url = f"{self.base_url}/store/search?q={quote_plus(app_name)}&c=apps"
        
        response = await self._retry_request(search_url)
        if not response:
            return []
        
        # Extract package name from search results
        package_match = re.search(r'id=([a-zA-Z0-9._]+)', response.text)
        if not package_match:
            logger.warning(f"Could not find package for app: {app_name}")
            return []
        
        package_name = package_match.group(1)
        logger.info(f"Found package {package_name} for app {app_name}")
        
        # Scrape reviews for the found package
        all_reviews = []
        for rating in [1, 2, 3]:
            reviews = await self._scrape_app_reviews(package_name, rating)
            all_reviews.extend(reviews)
        
        return all_reviews
    
    async def scrape_category_apps(self, category: str = "productivity") -> List[Dict[str, Any]]:
        """
        Scrape reviews from popular apps in a category
        
        Args:
            category: App category (productivity, social, etc.)
            
        Returns:
            List of review complaints from category apps
        """
        category_url = f"{self.base_url}/store/apps/category/{category.upper()}"
        
        response = await self._retry_request(category_url)
        if not response:
            return []
        
        # Extract package names from category page
        package_names = re.findall(r'id=([a-zA-Z0-9._]+)', response.text)
        
        # Limit to top apps to avoid too many requests
        top_packages = list(set(package_names))[:10]
        
        all_complaints = []
        for package_name in top_packages:
            for rating in [1, 2, 3]:
                reviews = await self._scrape_app_reviews(package_name, rating)
                all_complaints.extend(reviews)
        
        return all_complaints