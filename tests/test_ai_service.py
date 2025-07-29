"""
Unit tests for AI service
"""
import pytest
import json
from unittest.mock import Mock, patch, AsyncMock, mock_open
from app.services.ai_service import AIService


class TestAIService:
    """Test AI service functionality"""
    
    @pytest.fixture
    def mock_openai_response(self):
        """Create mock OpenAI response"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "idea": "An auto-save app that prevents data loss during crashes",
            "score_market": 8,
            "score_tech": 6,
            "score_competition": 7,
            "score_monetisation": 5,
            "score_feasibility": 9,
            "score_overall": 7
        })
        mock_response.model = "gpt-3.5-turbo"
        mock_response.usage = Mock()
        mock_response.usage.total_tokens = 450
        mock_response.usage.model_dump.return_value = {"total_tokens": 450}
        return mock_response
    
    @pytest.fixture
    def ai_service(self):
        """Create AI service instance with mock API key"""
        with patch('app.services.ai_service.settings') as mock_settings:
            mock_settings.openai_api_key = "test-api-key"
            return AIService()
    
    def test_init_with_api_key(self):
        """Test AI service initialization with API key"""
        service = AIService(api_key="test-key")
        assert service.api_key == "test-key"
        assert service.model == "gpt-3.5-turbo"
        assert service.max_tokens == 200
        assert service.temperature == 0.7
    
    def test_init_without_api_key_raises_error(self):
        """Test that missing API key raises error"""
        with patch('app.services.ai_service.settings') as mock_settings:
            mock_settings.openai_api_key = None
            
            with pytest.raises(ValueError, match="OpenAI API key is required"):
                AIService()
    
    def test_load_prompt_template_from_file(self):
        """Test loading prompt template from file"""
        mock_template = "Test prompt template with {complaint_text}"
        
        with patch('builtins.open', mock_open(read_data=mock_template)):
            with patch('pathlib.Path.exists', return_value=True):
                service = AIService(api_key="test-key")
                assert service.prompt_template == mock_template
    
    def test_load_prompt_template_fallback(self):
        """Test fallback to default template when file doesn't exist"""
        with patch('pathlib.Path.exists', return_value=False):
            service = AIService(api_key="test-key")
            assert "complaint_text" in service.prompt_template
            assert "JSON" in service.prompt_template
    
    @pytest.mark.asyncio
    async def test_generate_idea_success(self, ai_service, mock_openai_response):
        """Test successful idea generation"""
        with patch.object(ai_service, '_call_openai_api', return_value=mock_openai_response):
            result = await ai_service.generate_idea("This app keeps crashing")
            
            assert result['idea'] == "An auto-save app that prevents data loss during crashes"
            assert result['score_market'] == 8
            assert result['score_overall'] == 7
            assert result['tokens_used'] == 450
            assert 'raw_response' in result
    
    @pytest.mark.asyncio
    async def test_generate_idea_invalid_complaint(self, ai_service):
        """Test error handling for invalid complaint text"""
        with pytest.raises(ValueError, match="Complaint text must be at least 10 characters"):
            await ai_service.generate_idea("Bad")
        
        with pytest.raises(ValueError, match="Complaint text must be at least 10 characters"):
            await ai_service.generate_idea("")
    
    def test_parse_response_valid_json(self, ai_service, mock_openai_response):
        """Test parsing valid OpenAI response"""
        result = ai_service._parse_response(mock_openai_response)
        
        assert result['idea'] == "An auto-save app that prevents data loss during crashes"
        assert all(key in result for key in ['score_market', 'score_tech', 'score_competition'])
        assert result['raw_response']['model'] == "gpt-3.5-turbo"
    
    def test_parse_response_invalid_json(self, ai_service):
        """Test parsing invalid JSON response"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Invalid JSON content"
        
        with pytest.raises(ValueError, match="Invalid JSON response"):
            ai_service._parse_response(mock_response)
    
    def test_parse_response_missing_fields(self, ai_service):
        """Test parsing response with missing required fields"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "idea": "Test idea",
            "score_market": 8
            # Missing other required fields
        })
        
        with pytest.raises(ValueError, match="Missing required field"):
            ai_service._parse_response(mock_response)
    
    def test_parse_response_invalid_scores(self, ai_service):
        """Test parsing response with invalid score values"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "idea": "Test idea",
            "score_market": 15,  # Invalid score > 10
            "score_tech": 6,
            "score_competition": 7,
            "score_monetisation": 5,
            "score_feasibility": 9,
            "score_overall": 7
        })
        
        with pytest.raises(ValueError, match="Invalid score"):
            ai_service._parse_response(mock_response)
    
    def test_parse_response_empty_idea(self, ai_service):
        """Test parsing response with empty idea text"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "idea": "",  # Empty idea
            "score_market": 8,
            "score_tech": 6,
            "score_competition": 7,
            "score_monetisation": 5,
            "score_feasibility": 9,
            "score_overall": 7
        })
        
        with pytest.raises(ValueError, match="Idea text cannot be empty"):
            ai_service._parse_response(mock_response)
    
    @pytest.mark.asyncio
    async def test_call_openai_api_success(self, ai_service, mock_openai_response):
        """Test successful OpenAI API call"""
        with patch.object(ai_service.client.chat.completions, 'create', return_value=mock_openai_response) as mock_create:
            result = await ai_service._call_openai_api("test prompt")
            
            assert result == mock_openai_response
            mock_create.assert_called_once()
            call_args = mock_create.call_args
            assert call_args[1]['model'] == "gpt-3.5-turbo"
            assert call_args[1]['max_tokens'] == 200
            assert call_args[1]['temperature'] == 0.7
    
    @pytest.mark.asyncio
    async def test_call_openai_api_rate_limit(self, ai_service):
        """Test handling rate limit error"""
        from openai import RateLimitError
        
        mock_error = RateLimitError("Rate limit exceeded", response=Mock(), body=None)
        
        with patch.object(ai_service.client.chat.completions, 'create', side_effect=mock_error):
            with patch('asyncio.sleep') as mock_sleep:
                with pytest.raises(RateLimitError):
                    await ai_service._call_openai_api("test prompt")
                
                mock_sleep.assert_called_with(60)
    
    @pytest.mark.asyncio
    async def test_batch_generate_ideas(self, ai_service, mock_openai_response):
        """Test batch idea generation"""
        complaints = [
            "App crashes constantly",
            "UI is confusing and hard to use",
            "Loading times are too slow"
        ]
        
        with patch.object(ai_service, '_call_openai_api', return_value=mock_openai_response):
            results = await ai_service.batch_generate_ideas(complaints, max_concurrent=2)
            
            assert len(results) == 3
            
            # Check structure of results
            for complaint, idea_data, error in results:
                assert complaint in complaints
                if error is None:
                    assert idea_data is not None
                    assert 'idea' in idea_data
                    assert 'score_overall' in idea_data
    
    @pytest.mark.asyncio
    async def test_batch_generate_ideas_with_errors(self, ai_service):
        """Test batch generation with some failures"""
        complaints = ["Good complaint", "Bad"]  # Second will fail validation
        
        def mock_generate_side_effect(complaint):
            if len(complaint) < 10:
                raise ValueError("Too short")
            return {"idea": "Test idea", "score_overall": 7}
        
        with patch.object(ai_service, 'generate_idea', side_effect=mock_generate_side_effect):
            results = await ai_service.batch_generate_ideas(complaints)
            
            assert len(results) == 2
            assert results[0][1] is not None  # First should succeed
            assert results[0][2] is None
            assert results[1][1] is None     # Second should fail
            assert results[1][2] is not None
    
    def test_get_cost_estimate(self, ai_service):
        """Test cost estimation"""
        # Test with 1000 tokens
        cost = ai_service.get_cost_estimate(1000)
        assert cost == 0.002  # $0.002 per 1K tokens
        
        # Test with 500 tokens
        cost = ai_service.get_cost_estimate(500)
        assert cost == 0.001
    
    def test_get_total_cost_estimate(self, ai_service):
        """Test total cost estimation"""
        ai_service.total_tokens_used = 2000
        total_cost = ai_service.get_total_cost_estimate()
        assert total_cost == 0.004
    
    def test_reset_token_counter(self, ai_service):
        """Test resetting token counter"""
        ai_service.total_tokens_used = 1000
        ai_service.reset_token_counter()
        assert ai_service.total_tokens_used == 0
    
    @pytest.mark.asyncio
    async def test_test_connection_success(self, ai_service, mock_openai_response):
        """Test successful API connection test"""
        with patch.object(ai_service, '_call_openai_api', return_value=mock_openai_response):
            result = await ai_service.test_connection()
            assert result is True
    
    @pytest.mark.asyncio
    async def test_test_connection_failure(self, ai_service):
        """Test failed API connection test"""
        with patch.object(ai_service, '_call_openai_api', side_effect=Exception("API error")):
            result = await ai_service.test_connection()
            assert result is False