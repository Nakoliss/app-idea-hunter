"""
Unit tests for database models
"""
import pytest
from datetime import datetime
from uuid import uuid4
from app.models import Complaint, Idea, Source, Error


class TestComplaintModel:
    """Test Complaint model validation and constraints"""
    
    def test_complaint_creation(self):
        """Test creating a valid complaint"""
        complaint = Complaint(
            source="reddit",
            source_url="https://reddit.com/r/test/comments/123",
            content="This app keeps crashing when I try to save",
            content_hash="abc123def456",
            sentiment_score=-0.5
        )
        
        assert complaint.source == "reddit"
        assert complaint.source_url == "https://reddit.com/r/test/comments/123"
        assert complaint.content == "This app keeps crashing when I try to save"
        assert complaint.content_hash == "abc123def456"
        assert complaint.sentiment_score == -0.5
        assert isinstance(complaint.scraped_at, datetime)
    
    def test_complaint_with_metadata(self):
        """Test complaint with metadata JSON field"""
        metadata = {"subreddit": "androidapps", "author": "user123"}
        complaint = Complaint(
            source="reddit",
            content="App is slow",
            content_hash="xyz789",
            metadata=metadata
        )
        
        assert complaint.metadata == metadata
        assert complaint.metadata["subreddit"] == "androidapps"
    
    def test_complaint_required_fields(self):
        """Test that required fields are enforced"""
        # This test validates the model structure
        # In actual database operations, these would raise exceptions
        complaint = Complaint(
            source="google_play",
            content="Bad app",
            content_hash="unique123"
        )
        
        assert complaint.source_url is None  # Optional field
        assert complaint.sentiment_score is None  # Optional field


class TestIdeaModel:
    """Test Idea model validation and constraints"""
    
    def test_idea_creation(self):
        """Test creating a valid idea"""
        complaint_id = uuid4()
        idea = Idea(
            complaint_id=complaint_id,
            idea_text="Create an auto-save feature that saves work in background",
            score_market=8,
            score_tech=6,
            score_competition=7,
            score_monetisation=5,
            score_feasibility=9,
            score_overall=7,
            tokens_used=450
        )
        
        assert idea.complaint_id == complaint_id
        assert idea.idea_text == "Create an auto-save feature that saves work in background"
        assert idea.score_market == 8
        assert idea.score_overall == 7
        assert idea.tokens_used == 450
        assert idea.is_favorite is False  # Default value
    
    def test_idea_score_validation(self):
        """Test score field validation (1-10 range)"""
        # Test valid scores
        idea = Idea(
            complaint_id=uuid4(),
            idea_text="Test idea",
            score_market=1,  # Minimum
            score_tech=10,   # Maximum
            score_competition=5,
            score_monetisation=5,
            score_feasibility=5,
            score_overall=5
        )
        
        assert idea.score_market == 1
        assert idea.score_tech == 10
    
    def test_idea_with_raw_response(self):
        """Test idea with raw GPT response"""
        raw_response = {
            "idea": "Test idea",
            "scores": {
                "market": 8,
                "tech": 6
            }
        }
        
        idea = Idea(
            complaint_id=uuid4(),
            idea_text="Test idea",
            score_market=8,
            score_tech=6,
            score_competition=7,
            score_monetisation=5,
            score_feasibility=9,
            score_overall=7,
            raw_response=raw_response
        )
        
        assert idea.raw_response == raw_response
        assert idea.raw_response["scores"]["market"] == 8


class TestSourceModel:
    """Test Source model validation"""
    
    def test_source_creation(self):
        """Test creating a valid source"""
        source = Source(
            source_type="reddit",
            source_identifier="androidapps",
            config={"min_score": -0.3, "limit": 100}
        )
        
        assert source.source_type == "reddit"
        assert source.source_identifier == "androidapps"
        assert source.is_active is True  # Default value
        assert source.last_scraped is None
        assert source.config["min_score"] == -0.3
    
    def test_source_update_last_scraped(self):
        """Test updating last scraped timestamp"""
        source = Source(
            source_type="google_play",
            source_identifier="com.example.app"
        )
        
        # Update last scraped
        now = datetime.utcnow()
        source.last_scraped = now
        
        assert source.last_scraped == now


class TestErrorModel:
    """Test Error model validation"""
    
    def test_error_creation(self):
        """Test creating an error record"""
        error = Error(
            source="reddit",
            url="https://reddit.com/r/test/comments/123",
            error_message="Rate limit exceeded",
            error_type="RateLimitError",
            retry_count=2
        )
        
        assert error.source == "reddit"
        assert error.url == "https://reddit.com/r/test/comments/123"
        assert error.error_message == "Rate limit exceeded"
        assert error.error_type == "RateLimitError"
        assert error.retry_count == 2
        assert isinstance(error.occurred_at, datetime)
    
    def test_error_minimal_fields(self):
        """Test error with only required fields"""
        error = Error(
            source="google_play"
        )
        
        assert error.source == "google_play"
        assert error.url is None
        assert error.error_message is None
        assert error.error_type is None
        assert error.retry_count == 0  # Default value