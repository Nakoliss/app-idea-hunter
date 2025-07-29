"""
Unit tests for cost monitoring service
"""
import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import patch, mock_open
from app.services.cost_monitor import CostMonitor


class TestCostMonitor:
    """Test cost monitoring functionality"""
    
    @pytest.fixture
    def cost_monitor(self):
        """Create cost monitor instance"""
        with patch('app.services.cost_monitor.Path.exists', return_value=False):
            return CostMonitor()
    
    @pytest.fixture
    def sample_usage_data(self):
        """Create sample usage data"""
        now = datetime.utcnow()
        return [
            {
                'timestamp': (now - timedelta(hours=1)).isoformat(),
                'complaint_length': 100,
                'tokens_used': 450,
                'cost': 0.0009,
                'idea_generated': True,
                'tokens_per_char': 4.5
            },
            {
                'timestamp': (now - timedelta(hours=2)).isoformat(),
                'complaint_length': 80,
                'tokens_used': 380,
                'cost': 0.00076,
                'idea_generated': True,
                'tokens_per_char': 4.75
            },
            {
                'timestamp': (now - timedelta(hours=3)).isoformat(),
                'complaint_length': 120,
                'tokens_used': 520,
                'cost': 0.00104,
                'idea_generated': False,  # Failed generation
                'tokens_per_char': 4.33
            },
            {
                'timestamp': (now - timedelta(days=2)).isoformat(),  # Older data
                'complaint_length': 90,
                'tokens_used': 400,
                'cost': 0.0008,
                'idea_generated': True,
                'tokens_per_char': 4.44
            }
        ]
    
    def test_initialization(self, cost_monitor):
        """Test cost monitor initialization"""
        assert cost_monitor.max_tokens_per_complaint == 600  # From settings
        assert cost_monitor.cost_per_1k_tokens == 0.002
        assert cost_monitor.daily_usage_limit == 100.0
        assert isinstance(cost_monitor.usage_history, list)
    
    def test_load_usage_history(self):
        """Test loading usage history from file"""
        sample_data = [{"timestamp": "2024-01-01T10:00:00", "tokens_used": 400}]
        
        with patch('builtins.open', mock_open(read_data=json.dumps(sample_data))):
            with patch('app.services.cost_monitor.Path.exists', return_value=True):
                monitor = CostMonitor()
                assert len(monitor.usage_history) == 1
                assert monitor.usage_history[0]['tokens_used'] == 400
    
    def test_record_usage(self, cost_monitor):
        """Test recording usage data"""
        cost_monitor.record_usage(
            complaint_text="This is a test complaint",
            tokens_used=450,
            cost=0.0009,
            idea_generated=True
        )
        
        assert len(cost_monitor.usage_history) == 1
        record = cost_monitor.usage_history[0]
        assert record['tokens_used'] == 450
        assert record['cost'] == 0.0009
        assert record['idea_generated'] is True
        assert record['complaint_length'] == len("This is a test complaint")
    
    def test_get_mean_tokens_per_complaint(self, cost_monitor, sample_usage_data):
        """Test calculating mean tokens per complaint"""
        cost_monitor.usage_history = sample_usage_data
        
        # Should only count successful generations from last 7 days
        mean = cost_monitor.get_mean_tokens_per_complaint(days=7)
        
        # Only first two records are successful and within 7 days
        expected_mean = (450 + 380) / 2
        assert abs(mean - expected_mean) < 0.1
    
    def test_get_mean_tokens_empty_history(self, cost_monitor):
        """Test mean calculation with empty history"""
        mean = cost_monitor.get_mean_tokens_per_complaint()
        assert mean == 0.0
    
    def test_check_cost_guard_pass(self, cost_monitor, sample_usage_data):
        """Test cost guard check that passes"""
        cost_monitor.usage_history = sample_usage_data
        cost_monitor.max_tokens_per_complaint = 500  # Set higher threshold
        
        result = cost_monitor.check_cost_guard()
        
        assert result['passed'] is True
        assert result['threshold_exceeded'] is False
        assert result['mean_tokens_per_complaint'] <= result['threshold']
    
    def test_check_cost_guard_fail(self, cost_monitor, sample_usage_data):
        """Test cost guard check that fails"""
        cost_monitor.usage_history = sample_usage_data
        cost_monitor.max_tokens_per_complaint = 300  # Set lower threshold
        
        result = cost_monitor.check_cost_guard()
        
        assert result['passed'] is False
        assert result['threshold_exceeded'] is True
        assert result['mean_tokens_per_complaint'] > result['threshold']
    
    def test_get_total_cost(self, cost_monitor, sample_usage_data):
        """Test total cost calculation"""
        cost_monitor.usage_history = sample_usage_data
        
        # Get cost for last day (first 3 records)
        total_cost = cost_monitor.get_total_cost(days=1)
        expected_cost = 0.0009 + 0.00076 + 0.00104
        assert abs(total_cost - expected_cost) < 0.00001
    
    def test_check_daily_limit_normal(self, cost_monitor, sample_usage_data):
        """Test daily limit check under normal usage"""
        cost_monitor.usage_history = sample_usage_data
        
        result = cost_monitor.check_daily_limit()
        
        assert result['limit_exceeded'] is False
        assert result['daily_cost'] < result['daily_limit']
        assert result['remaining_budget'] > 0
    
    def test_check_daily_limit_exceeded(self, cost_monitor):
        """Test daily limit check when exceeded"""
        # Create usage that exceeds daily limit
        high_usage = [
            {
                'timestamp': datetime.utcnow().isoformat(),
                'tokens_used': 50000000,  # Very high usage
                'cost': 150.0,  # Above daily limit
                'idea_generated': True
            }
        ]
        cost_monitor.usage_history = high_usage
        
        result = cost_monitor.check_daily_limit()
        
        assert result['limit_exceeded'] is True
        assert result['daily_cost'] > result['daily_limit']
        assert result['remaining_budget'] == 0
    
    def test_get_usage_statistics(self, cost_monitor, sample_usage_data):
        """Test usage statistics calculation"""
        cost_monitor.usage_history = sample_usage_data
        
        stats = cost_monitor.get_usage_statistics(days=7)
        
        assert stats['total_requests'] == 3  # First 3 records within 7 days
        assert stats['successful_requests'] == 2  # Only 2 successful
        assert stats['failed_requests'] == 1
        assert stats['success_rate'] == 2/3
        assert stats['mean_tokens'] == (450 + 380) / 2  # Only successful ones
    
    def test_get_usage_statistics_empty(self, cost_monitor):
        """Test usage statistics with empty history"""
        stats = cost_monitor.get_usage_statistics()
        
        assert stats['total_requests'] == 0
        assert stats['successful_requests'] == 0
        assert stats['total_cost'] == 0.0
        assert stats['mean_tokens'] == 0.0
    
    def test_should_continue_processing_normal(self, cost_monitor, sample_usage_data):
        """Test processing continuation under normal conditions"""
        cost_monitor.usage_history = sample_usage_data
        cost_monitor.max_tokens_per_complaint = 500  # Higher threshold
        
        assert cost_monitor.should_continue_processing() is True
    
    def test_should_continue_processing_cost_guard_fail(self, cost_monitor, sample_usage_data):
        """Test processing stops when cost guard fails"""
        cost_monitor.usage_history = sample_usage_data
        cost_monitor.max_tokens_per_complaint = 300  # Lower threshold
        
        assert cost_monitor.should_continue_processing() is False
    
    def test_should_continue_processing_daily_limit_exceeded(self, cost_monitor):
        """Test processing stops when daily limit exceeded"""
        high_usage = [
            {
                'timestamp': datetime.utcnow().isoformat(),
                'tokens_used': 50000000,
                'cost': 150.0,  # Above daily limit
                'idea_generated': True
            }
        ]
        cost_monitor.usage_history = high_usage
        
        assert cost_monitor.should_continue_processing() is False
    
    def test_estimate_batch_cost(self, cost_monitor, sample_usage_data):
        """Test batch cost estimation"""
        cost_monitor.usage_history = sample_usage_data
        
        estimate = cost_monitor.estimate_batch_cost(10)
        
        assert estimate['complaint_count'] == 10
        assert estimate['estimated_tokens_per_complaint'] == (450 + 380) / 2  # Mean from successful
        assert estimate['total_estimated_tokens'] == estimate['estimated_tokens_per_complaint'] * 10
        assert estimate['estimated_cost'] > 0
        assert 'can_afford' in estimate
        assert 'max_affordable_complaints' in estimate
    
    def test_estimate_batch_cost_no_history(self, cost_monitor):
        """Test batch cost estimation with no history"""
        estimate = cost_monitor.estimate_batch_cost(5)
        
        assert estimate['complaint_count'] == 5
        assert estimate['estimated_tokens_per_complaint'] == 400  # Default estimate
        assert estimate['total_estimated_tokens'] == 2000
    
    def test_clear_usage_history(self, cost_monitor, sample_usage_data):
        """Test clearing usage history"""
        cost_monitor.usage_history = sample_usage_data
        assert len(cost_monitor.usage_history) > 0
        
        cost_monitor.clear_usage_history()
        assert len(cost_monitor.usage_history) == 0
    
    def test_export_usage_data(self, cost_monitor, sample_usage_data):
        """Test exporting usage data"""
        cost_monitor.usage_history = sample_usage_data
        
        with patch('builtins.open', mock_open()) as mock_file:
            cost_monitor.export_usage_data('test_export.json')
            
            mock_file.assert_called_once_with('test_export.json', 'w')
            # Verify JSON was written
            handle = mock_file()
            written_content = ''.join(call.args[0] for call in handle.write.call_args_list)
            assert 'timestamp' in written_content
            assert 'tokens_used' in written_content