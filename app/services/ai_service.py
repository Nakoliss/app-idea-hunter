"""
AI service for generating startup ideas using OpenAI GPT-3.5
"""
import json
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import openai
from openai import AsyncOpenAI
from app.config import settings
from app.logging_config import logger


class AIService:
    """Service for generating startup ideas from complaints using GPT-3.5"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize AI service
        
        Args:
            api_key: OpenAI API key (uses settings if not provided)
        """
        self.api_key = api_key or settings.OPENAI_API_KEY
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        
        self.client = AsyncOpenAI(api_key=self.api_key)
        self.model = "gpt-3.5-turbo"
        self.max_tokens = 200
        self.temperature = 0.7
        self.prompt_template = self._load_prompt_template()
        self.total_tokens_used = 0
        
        logger.info("AI service initialized with GPT-3.5")
    
    def _load_prompt_template(self) -> str:
        """
        Load prompt template from file
        
        Returns:
            Prompt template string
        """
        try:
            prompt_file = Path("prompts/idea_prompt.txt")
            if not prompt_file.exists():
                # Fallback to a simple template if file doesn't exist
                return self._get_default_prompt_template()
            
            with open(prompt_file, 'r', encoding='utf-8') as f:
                template = f.read()
                
            logger.info("Loaded prompt template from file")
            return template
            
        except Exception as e:
            logger.warning(f"Error loading prompt template: {str(e)}, using default")
            return self._get_default_prompt_template()
    
    def _get_default_prompt_template(self) -> str:
        """
        Get default prompt template as fallback
        
        Returns:
            Default prompt template
        """
        return """You are an expert startup advisor analyzing user complaints to generate viable app ideas.

Given the following complaint, generate a concise startup idea that directly addresses the pain point. Your response must be valid JSON with the following structure:

{
  "idea": "A concise app idea description under 35 words that directly solves the complaint",
  "score_market": 8,
  "score_tech": 6,
  "score_competition": 7,
  "score_monetisation": 5,
  "score_feasibility": 9,
  "score_overall": 7
}

Scoring criteria (1-10 scale):
- market: Size and demand for this solution
- tech: Technical complexity and feasibility
- competition: How crowded the market is (lower = less competition)
- monetisation: Revenue potential and business model viability
- feasibility: Overall likelihood of successful execution
- overall: Weighted average considering all factors

Complaint: {complaint_text}

Respond only with valid JSON, no additional text."""
    
    async def generate_idea(self, complaint_text: str) -> Dict[str, Any]:
        """
        Generate a startup idea from a complaint
        
        Args:
            complaint_text: The complaint text to analyze
            
        Returns:
            Dictionary with idea and scores
            
        Raises:
            ValueError: If the complaint text is invalid
            Exception: If the API call fails
        """
        if not complaint_text or len(complaint_text.strip()) < 10:
            raise ValueError("Complaint text must be at least 10 characters")
        
        # Prepare prompt
        prompt = self.prompt_template.format(complaint_text=complaint_text.strip())
        
        try:
            # Make API call
            response = await self._call_openai_api(prompt)
            
            # Parse and validate response
            idea_data = self._parse_response(response)
            
            # Track tokens
            tokens_used = response.usage.total_tokens if response.usage else 0
            self.total_tokens_used += tokens_used
            idea_data['tokens_used'] = tokens_used
            
            logger.debug(f"Generated idea for complaint, tokens used: {tokens_used}")
            return idea_data
            
        except Exception as e:
            logger.error(f"Error generating idea: {str(e)}")
            raise
    
    async def _call_openai_api(self, prompt: str) -> Any:
        """
        Make API call to OpenAI
        
        Args:
            prompt: The prompt to send
            
        Returns:
            OpenAI response object
        """
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a startup advisor who responds only with valid JSON."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                response_format={"type": "json_object"}
            )
            
            return response
            
        except openai.RateLimitError as e:
            logger.warning(f"OpenAI rate limit hit: {str(e)}")
            await asyncio.sleep(60)  # Wait 1 minute
            raise
            
        except openai.APIError as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise
            
        except Exception as e:
            logger.error(f"Unexpected error calling OpenAI: {str(e)}")
            raise
    
    def _parse_response(self, response: Any) -> Dict[str, Any]:
        """
        Parse and validate OpenAI response
        
        Args:
            response: OpenAI response object
            
        Returns:
            Parsed and validated idea data
            
        Raises:
            ValueError: If response format is invalid
        """
        try:
            # Extract content
            content = response.choices[0].message.content
            
            # Parse JSON
            idea_data = json.loads(content)
            
            # Validate required fields
            required_fields = [
                'idea', 'score_market', 'score_tech', 'score_competition',
                'score_monetisation', 'score_feasibility', 'score_overall'
            ]
            
            for field in required_fields:
                if field not in idea_data:
                    raise ValueError(f"Missing required field: {field}")
            
            # Validate score ranges
            score_fields = [f for f in required_fields if f.startswith('score_')]
            for field in score_fields:
                score = idea_data[field]
                if not isinstance(score, int) or not 1 <= score <= 10:
                    raise ValueError(f"Invalid score for {field}: {score}")
            
            # Validate idea text length
            idea_text = idea_data['idea']
            if not isinstance(idea_text, str) or len(idea_text.strip()) == 0:
                raise ValueError("Idea text cannot be empty")
            
            if len(idea_text.split()) > 35:
                logger.warning(f"Idea text exceeds 35 words: {len(idea_text.split())} words")
            
            # Store raw response
            idea_data['raw_response'] = {
                'content': content,
                'model': response.model,
                'usage': response.usage.model_dump() if response.usage else None
            }
            
            return idea_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in OpenAI response: {str(e)}")
            raise ValueError(f"Invalid JSON response: {str(e)}")
            
        except Exception as e:
            logger.error(f"Error parsing OpenAI response: {str(e)}")
            raise
    
    async def batch_generate_ideas(
        self, 
        complaints: List[str],
        max_concurrent: int = 5
    ) -> List[Tuple[str, Optional[Dict[str, Any]], Optional[str]]]:
        """
        Generate ideas for multiple complaints in parallel
        
        Args:
            complaints: List of complaint texts
            max_concurrent: Maximum concurrent API calls
            
        Returns:
            List of tuples (complaint, idea_data or None, error_message or None)
        """
        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_complaint(complaint_text: str) -> Tuple[str, Optional[Dict[str, Any]], Optional[str]]:
            async with semaphore:
                try:
                    idea_data = await self.generate_idea(complaint_text)
                    return complaint_text, idea_data, None
                except Exception as e:
                    error_msg = str(e)
                    logger.error(f"Error processing complaint: {error_msg}")
                    return complaint_text, None, error_msg
        
        # Process all complaints concurrently
        tasks = [process_complaint(complaint) for complaint in complaints]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions from gather
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_msg = str(result)
                processed_results.append((complaints[i], None, error_msg))
            else:
                processed_results.append(result)
        
        success_count = sum(1 for _, idea, _ in processed_results if idea is not None)
        logger.info(f"Batch processing completed: {success_count}/{len(complaints)} successful")
        
        return processed_results
    
    def get_cost_estimate(self, token_count: int) -> float:
        """
        Estimate cost based on token usage
        
        Args:
            token_count: Number of tokens used
            
        Returns:
            Estimated cost in USD
        """
        # GPT-3.5-turbo pricing (as of 2024)
        cost_per_1k_tokens = 0.002  # $0.002 per 1K tokens
        return (token_count / 1000) * cost_per_1k_tokens
    
    def get_total_cost_estimate(self) -> float:
        """
        Get total estimated cost for all API calls made
        
        Returns:
            Total estimated cost in USD
        """
        return self.get_cost_estimate(self.total_tokens_used)
    
    def reset_token_counter(self):
        """Reset the total token usage counter"""
        self.total_tokens_used = 0
        logger.info("Token usage counter reset")
    
    async def test_connection(self) -> bool:
        """
        Test OpenAI API connection
        
        Returns:
            True if connection is successful
        """
        try:
            test_response = await self.generate_idea(
                "This is a test complaint to verify API connectivity"
            )
            logger.info("OpenAI API connection test successful")
            return True
        except Exception as e:
            logger.error(f"OpenAI API connection test failed: {str(e)}")
            return False