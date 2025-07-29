"""
Unit tests for deduplication service
"""
import pytest
from app.services.deduplication_service import DeduplicationService


class TestDeduplicationService:
    """Test deduplication functionality"""
    
    @pytest.fixture
    def dedup_service(self):
        """Create deduplication service instance"""
        return DeduplicationService(token_limit=120)
    
    def test_tokenize(self, dedup_service):
        """Test text tokenization"""
        text = "This is a TEST sentence with CAPS and punctuation!"
        tokens = dedup_service._tokenize(text)
        
        assert tokens == ['this', 'is', 'a', 'test', 'sentence', 'with', 'caps', 'and', 'punctuation']
        
    def test_tokenize_with_urls(self, dedup_service):
        """Test tokenization removes URLs"""
        text = "Check out https://example.com for more info and http://test.org"
        tokens = dedup_service._tokenize(text)
        
        assert 'https' not in tokens
        assert 'example' not in tokens
        assert 'com' not in tokens
        assert tokens == ['check', 'out', 'for', 'more', 'info', 'and']
    
    def test_generate_hash(self, dedup_service):
        """Test hash generation"""
        text = "This app keeps crashing when I try to save my work"
        hash1 = dedup_service.generate_hash(text)
        
        # Hash should be 40 characters (SHA-1)
        assert len(hash1) == 40
        assert all(c in '0123456789abcdef' for c in hash1)
        
        # Same text should produce same hash
        hash2 = dedup_service.generate_hash(text)
        assert hash1 == hash2
    
    def test_hash_case_insensitive(self, dedup_service):
        """Test that hashing is case insensitive"""
        text1 = "This App Is BROKEN"
        text2 = "this app is broken"
        
        hash1 = dedup_service.generate_hash(text1)
        hash2 = dedup_service.generate_hash(text2)
        
        assert hash1 == hash2
    
    def test_hash_token_limit(self, dedup_service):
        """Test that hash uses only first N tokens"""
        # Create service with small token limit
        limited_service = DeduplicationService(token_limit=5)
        
        text1 = "This app is completely broken and needs to be fixed immediately"
        text2 = "This app is completely broken but works fine on other devices"
        
        # Both should have same hash (first 5 tokens are same)
        hash1 = limited_service.generate_hash(text1)
        hash2 = limited_service.generate_hash(text2)
        
        assert hash1 == hash2
    
    def test_is_duplicate_with_cache(self, dedup_service):
        """Test duplicate detection using internal cache"""
        text1 = "The app crashes constantly"
        text2 = "The app crashes constantly"  # Exact duplicate
        text3 = "Different complaint about bugs"
        
        # Add first text to cache
        dedup_service.add_to_cache(text1)
        
        # Check duplicates
        assert dedup_service.is_duplicate(text2) is True
        assert dedup_service.is_duplicate(text3) is False
    
    def test_is_duplicate_with_external_hashes(self, dedup_service):
        """Test duplicate detection with provided hash set"""
        text = "App keeps freezing"
        text_hash = dedup_service.generate_hash(text)
        
        existing_hashes = {text_hash, "other_hash_123"}
        
        assert dedup_service.is_duplicate(text, existing_hashes) is True
        assert dedup_service.is_duplicate("New complaint", existing_hashes) is False
    
    def test_cache_operations(self, dedup_service):
        """Test cache management operations"""
        # Initially empty
        assert dedup_service.get_cache_size() == 0
        
        # Add some hashes
        dedup_service.add_to_cache("Complaint 1")
        dedup_service.add_to_cache("Complaint 2")
        dedup_service.add_to_cache("Complaint 3")
        
        assert dedup_service.get_cache_size() == 3
        
        # Clear cache
        dedup_service.clear_cache()
        assert dedup_service.get_cache_size() == 0
    
    def test_batch_check_duplicates(self, dedup_service):
        """Test batch duplicate checking"""
        texts = [
            "This app is terrible",
            "The service is broken",
            "This app is terrible",  # Duplicate of first
            "New unique complaint",
            "The service is broken"  # Duplicate of second
        ]
        
        results = dedup_service.batch_check_duplicates(texts)
        
        assert len(results) == 5
        
        # Check structure
        for text, hash_val, is_dup in results:
            assert isinstance(text, str)
            assert isinstance(hash_val, str)
            assert len(hash_val) == 40
            assert isinstance(is_dup, bool)
        
        # First two should not be duplicates
        assert results[0][2] is False
        assert results[1][2] is False
        
        # Third and fifth should be duplicates
        assert results[2][2] is True
        assert results[4][2] is True
        
        # Fourth should not be duplicate
        assert results[3][2] is False
    
    def test_empty_text_hash(self, dedup_service):
        """Test handling empty text"""
        hash_val = dedup_service.generate_hash("")
        
        # Should still generate a valid hash
        assert len(hash_val) == 40
        assert all(c in '0123456789abcdef' for c in hash_val)
    
    def test_special_characters(self, dedup_service):
        """Test handling special characters and emojis"""
        text = "This app is 💔 broken!!! #fail @support"
        tokens = dedup_service._tokenize(text)
        
        # Should only keep alphanumeric tokens
        assert 'fail' in tokens
        assert 'support' in tokens
        assert '💔' not in tokens
        assert '!!!' not in tokens
        assert '#' not in tokens
        assert '@' not in tokens