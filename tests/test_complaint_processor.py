"""
Unit tests for complaint processing pipeline
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from app.services.complaint_processor import ComplaintProcessor
from app.models import Complaint


class TestComplaintProcessor:
    """Test complaint processing pipeline"""
    
    @pytest.fixture
    def processor(self):
        """Create complaint processor instance"""
        return ComplaintProcessor(sentiment_threshold=-0.3, token_limit=120)
    
    @pytest.mark.asyncio
    async def test_process_complaint_negative(self, processor):
        """Test processing a valid negative complaint"""
        complaint = await processor.process_complaint(
            content="This app is terrible and crashes constantly",
            source="reddit",
            source_url="https://reddit.com/r/test/123",
            metadata={"subreddit": "androidapps"}
        )
        
        assert complaint is not None
        assert complaint.source == "reddit"
        assert complaint.sentiment_score < -0.3
        assert len(complaint.content_hash) == 40
        assert complaint.metadata["subreddit"] == "androidapps"
    
    @pytest.mark.asyncio
    async def test_process_complaint_positive_filtered(self, processor):
        """Test that positive complaints are filtered out"""
        complaint = await processor.process_complaint(
            content="This app is amazing and works perfectly!",
            source="google_play",
            source_url="https://play.google.com/store/apps/details?id=test"
        )
        
        assert complaint is None
    
    @pytest.mark.asyncio
    async def test_process_complaint_duplicate_filtered(self, processor):
        """Test that duplicate complaints are filtered out"""
        # First complaint
        complaint1 = await processor.process_complaint(
            content="The app keeps freezing on startup",
            source="reddit"
        )
        
        assert complaint1 is not None
        
        # Add hash to existing set
        existing_hashes = {complaint1.content_hash}
        
        # Try to process duplicate
        complaint2 = await processor.process_complaint(
            content="The app keeps freezing on startup",  # Same content
            source="google_play",
            existing_hashes=existing_hashes
        )
        
        assert complaint2 is None
    
    @pytest.mark.asyncio
    async def test_load_existing_hashes(self, processor):
        """Test loading existing hashes from database"""
        # Mock database session
        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter([
            ("hash1",), ("hash2",), ("hash3",)
        ]))
        mock_session.execute.return_value = mock_result
        
        hashes = await processor.load_existing_hashes(mock_session)
        
        assert len(hashes) == 3
        assert "hash1" in hashes
        assert "hash2" in hashes
        assert "hash3" in hashes
    
    @pytest.mark.asyncio
    async def test_batch_process_complaints(self, processor):
        """Test batch processing of complaints"""
        complaints_data = [
            {
                "content": "This app is horrible and never works",
                "source": "reddit",
                "source_url": "https://reddit.com/1"
            },
            {
                "content": "Great app, love it!",  # Positive - filtered
                "source": "google_play"
            },
            {
                "content": "This app is horrible and never works",  # Duplicate
                "source": "google_play"
            },
            {
                "content": "The service is broken and support is useless",
                "source": "reddit"
            },
            {
                "content": "",  # Empty content - error
                "source": "reddit"
            }
        ]
        
        processed, stats = await processor.batch_process_complaints(complaints_data)
        
        # Should process 2 valid complaints (first and fourth)
        assert len(processed) == 2
        assert stats['total'] == 5
        assert stats['processed'] == 2
        assert stats['filtered_sentiment'] == 1
        assert stats['filtered_duplicate'] == 1
        assert stats['errors'] == 1
        
        # Check processed complaints
        assert processed[0].content == complaints_data[0]['content']
        assert processed[1].content == complaints_data[3]['content']
    
    @pytest.mark.asyncio
    async def test_batch_process_with_session(self, processor):
        """Test batch processing with database session"""
        # Mock session with existing hashes
        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter([("existing_hash",)]))
        mock_session.execute.return_value = mock_result
        
        complaints_data = [
            {
                "content": "New complaint about bugs",
                "source": "reddit"
            }
        ]
        
        # Mock the hash generation to return our known hash
        with patch.object(processor.deduplication_service, 'generate_hash') as mock_hash:
            # First call for existing hash check
            mock_hash.return_value = "new_hash"
            
            processed, stats = await processor.batch_process_complaints(
                complaints_data, 
                session=mock_session
            )
            
            # Should process the complaint since it's not a duplicate
            assert len(processed) == 1
            assert stats['processed'] == 1
    
    def test_reset_cache(self, processor):
        """Test cache reset functionality"""
        # Add some items to cache
        processor.deduplication_service.add_to_cache("Test 1")
        processor.deduplication_service.add_to_cache("Test 2")
        
        assert processor.deduplication_service.get_cache_size() > 0
        
        # Reset cache
        processor.reset_cache()
        
        assert processor.deduplication_service.get_cache_size() == 0
    
    @pytest.mark.asyncio
    async def test_process_complaint_with_error(self, processor):
        """Test error handling in complaint processing"""
        # Mock sentiment analyzer to raise error
        with patch.object(processor.sentiment_analyzer, 'analyze') as mock_analyze:
            mock_analyze.side_effect = Exception("Analysis error")
            
            complaint = await processor.process_complaint(
                content="Test complaint",
                source="reddit"
            )
            
            assert complaint is None