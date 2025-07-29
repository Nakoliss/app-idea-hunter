"""
Unit tests for sentiment analysis service
"""
import pytest
from app.services.sentiment_analyzer import SentimentAnalyzer


class TestSentimentAnalyzer:
    """Test sentiment analysis functionality"""
    
    @pytest.fixture
    def analyzer(self):
        """Create sentiment analyzer instance"""
        return SentimentAnalyzer(threshold=-0.3)
    
    def test_analyze_negative_sentiment(self, analyzer):
        """Test analyzing clearly negative text"""
        negative_texts = [
            "This app is terrible and keeps crashing all the time",
            "I hate this service, it's completely useless",
            "Worst experience ever, totally disappointed",
            "The app is broken and the support is horrible"
        ]
        
        for text in negative_texts:
            score = analyzer.analyze(text)
            assert score < 0, f"Expected negative score for: {text}"
            assert analyzer.is_negative_complaint(text) is True
    
    def test_analyze_positive_sentiment(self, analyzer):
        """Test analyzing clearly positive text"""
        positive_texts = [
            "This app is amazing and works perfectly",
            "I love this service, it's incredibly helpful",
            "Best experience ever, highly recommend",
            "The app is fantastic and the support is excellent"
        ]
        
        for text in positive_texts:
            score = analyzer.analyze(text)
            assert score > 0, f"Expected positive score for: {text}"
            assert analyzer.is_negative_complaint(text) is False
    
    def test_analyze_neutral_sentiment(self, analyzer):
        """Test analyzing neutral text"""
        neutral_texts = [
            "The app has a blue interface",
            "I opened the application today",
            "The service is available on weekdays"
        ]
        
        for text in neutral_texts:
            score = analyzer.analyze(text)
            # Neutral texts should have scores close to 0
            assert -0.3 <= score <= 0.3, f"Expected neutral score for: {text}"
    
    def test_sentiment_threshold(self):
        """Test custom sentiment threshold"""
        # Create analyzer with stricter threshold
        strict_analyzer = SentimentAnalyzer(threshold=-0.5)
        
        # Mildly negative text
        text = "The app is not very good"
        score = strict_analyzer.analyze(text)
        
        # Should not be considered negative with stricter threshold
        if score > -0.5:
            assert strict_analyzer.is_negative_complaint(text) is False
    
    def test_batch_analyze(self, analyzer):
        """Test batch sentiment analysis"""
        texts = [
            "This app is terrible",  # Negative
            "Great service!",  # Positive
            "The worst app ever",  # Negative
            "It's okay",  # Neutral/Mild
        ]
        
        results = analyzer.batch_analyze(texts)
        
        assert len(results) == 4
        
        # Check structure of results
        for text, score, is_negative in results:
            assert isinstance(text, str)
            assert isinstance(score, float)
            assert isinstance(is_negative, bool)
            assert -1 <= score <= 1
        
        # Verify specific results
        assert results[0][2] is True  # First text is negative
        assert results[1][2] is False  # Second text is positive
        assert results[2][2] is True  # Third text is negative
    
    def test_get_detailed_scores(self, analyzer):
        """Test getting detailed sentiment scores"""
        text = "This app is absolutely terrible but the UI looks nice"
        
        scores = analyzer.get_detailed_scores(text)
        
        assert 'compound' in scores
        assert 'positive' in scores
        assert 'negative' in scores
        assert 'neutral' in scores
        
        # All scores should be between 0 and 1 except compound
        assert -1 <= scores['compound'] <= 1
        assert 0 <= scores['positive'] <= 1
        assert 0 <= scores['negative'] <= 1
        assert 0 <= scores['neutral'] <= 1
        
        # Sum of pos, neg, neu should be approximately 1
        total = scores['positive'] + scores['negative'] + scores['neutral']
        assert 0.99 <= total <= 1.01
    
    def test_empty_text(self, analyzer):
        """Test handling empty text"""
        score = analyzer.analyze("")
        assert score == 0.0
        assert analyzer.is_negative_complaint("") is False
    
    def test_very_long_text(self, analyzer):
        """Test handling very long text"""
        # Create a long complaint
        long_text = "This app is terrible. " * 100
        
        score = analyzer.analyze(long_text)
        assert score < -0.3
        assert analyzer.is_negative_complaint(long_text) is True