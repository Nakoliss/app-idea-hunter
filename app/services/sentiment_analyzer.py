"""
VADER sentiment analysis service for filtering complaints
"""
from typing import Optional
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from app.logging_config import logger


class SentimentAnalyzer:
    """Service for analyzing sentiment of text using VADER"""
    
    def __init__(self, threshold: float = -0.3):
        """
        Initialize sentiment analyzer
        
        Args:
            threshold: Sentiment score threshold for filtering (default: -0.3)
        """
        self.analyzer = SentimentIntensityAnalyzer()
        self.threshold = threshold
        logger.info(f"Sentiment analyzer initialized with threshold: {threshold}")
    
    def analyze(self, text: str) -> float:
        """
        Analyze sentiment of text and return compound score
        
        Args:
            text: Text to analyze
            
        Returns:
            Compound sentiment score (-1 to 1)
        """
        try:
            scores = self.analyzer.polarity_scores(text)
            compound_score = scores['compound']
            
            logger.debug(f"Sentiment analysis - Text length: {len(text)}, Score: {compound_score}")
            return compound_score
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {str(e)}")
            raise
    
    def is_negative_complaint(self, text: str) -> bool:
        """
        Check if text is a negative complaint based on sentiment threshold
        
        Args:
            text: Text to analyze
            
        Returns:
            True if sentiment score is below threshold
        """
        score = self.analyze(text)
        is_negative = score < self.threshold
        
        if is_negative:
            logger.debug(f"Negative complaint detected with score {score}")
        
        return is_negative
    
    def batch_analyze(self, texts: list[str]) -> list[tuple[str, float, bool]]:
        """
        Analyze sentiment for multiple texts
        
        Args:
            texts: List of texts to analyze
            
        Returns:
            List of tuples (text, sentiment_score, is_negative)
        """
        results = []
        
        for text in texts:
            try:
                score = self.analyze(text)
                is_negative = score < self.threshold
                results.append((text, score, is_negative))
            except Exception as e:
                logger.error(f"Error in batch analysis for text: {text[:50]}... Error: {str(e)}")
                # Skip failed items but continue processing
                continue
        
        logger.info(f"Batch sentiment analysis completed - {len(results)}/{len(texts)} successful")
        return results
    
    def get_detailed_scores(self, text: str) -> dict:
        """
        Get detailed sentiment scores including positive, negative, neutral components
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary with all sentiment scores
        """
        try:
            scores = self.analyzer.polarity_scores(text)
            return {
                'compound': scores['compound'],
                'positive': scores['pos'],
                'negative': scores['neg'],
                'neutral': scores['neu']
            }
        except Exception as e:
            logger.error(f"Error getting detailed scores: {str(e)}")
            raise