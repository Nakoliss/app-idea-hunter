"""
Cost guard tests to ensure mean tokens per complaint stays under threshold
"""
import pytest
import json
from pathlib import Path
from app.services.cost_monitor import CostMonitor


class TestCostGuard:
    """Test cost guard functionality"""
    
    def test_cost_guard_threshold_not_exceeded(self):
        """Test that mean tokens per complaint is under threshold"""
        monitor = CostMonitor()
        
        # Load sample data
        sample_file = Path("sample_tokens.json")
        if sample_file.exists():
            with open(sample_file, 'r') as f:
                sample_data = json.load(f)
            monitor.usage_history = sample_data
        
        # Check cost guard
        result = monitor.check_cost_guard(days=30)
        
        # The test should pass - mean tokens should be under 600
        assert result['passed'], f"Cost guard failed: mean tokens ({result['mean_tokens_per_complaint']:.1f}) exceeds threshold ({result['threshold']})"
        assert result['mean_tokens_per_complaint'] <= monitor.max_tokens_per_complaint
    
    def test_cost_calculation(self):
        """Test cost calculation accuracy"""
        monitor = CostMonitor()
        
        # Test known values
        tokens = 1000
        expected_cost = 0.002  # $0.002 per 1K tokens for GPT-3.5
        
        calculated_cost = (tokens / 1000) * monitor.cost_per_1k_tokens
        assert abs(calculated_cost - expected_cost) < 0.0001
    
    def test_usage_recording(self):
        """Test usage recording functionality"""
        monitor = CostMonitor()
        monitor.usage_history = []  # Start fresh
        
        # Record usage
        monitor.record_usage(
            complaint_text="This is a test complaint about app issues",
            tokens_used=450,
            cost=0.0009,
            idea_generated=True
        )
        
        assert len(monitor.usage_history) == 1
        record = monitor.usage_history[0]
        assert record['tokens_used'] == 450
        assert record['cost'] == 0.0009
        assert record['idea_generated'] is True
    
    def test_mean_calculation_with_sample_data(self):
        """Test mean calculation with known sample data"""
        monitor = CostMonitor()
        
        # Use sample data from file
        sample_data = [
            {
                "timestamp": "2024-01-01T10:00:00",
                "tokens_used": 400,
                "idea_generated": True
            },
            {
                "timestamp": "2024-01-01T10:05:00", 
                "tokens_used": 500,
                "idea_generated": True
            },
            {
                "timestamp": "2024-01-01T10:10:00",
                "tokens_used": 300,
                "idea_generated": True
            }
        ]
        
        monitor.usage_history = sample_data
        mean = monitor.get_mean_tokens_per_complaint(days=30)
        
        expected_mean = (400 + 500 + 300) / 3
        assert abs(mean - expected_mean) < 0.1
    
    def test_daily_limit_check(self):
        """Test daily spending limit check"""
        monitor = CostMonitor()
        monitor.usage_history = []
        
        # Add some recent usage
        monitor.record_usage("test", 1000, 0.002, True)
        monitor.record_usage("test", 1000, 0.002, True)
        
        daily_check = monitor.check_daily_limit()
        
        assert 'daily_cost' in daily_check
        assert 'daily_limit' in daily_check
        assert 'limit_exceeded' in daily_check
        assert daily_check['daily_cost'] > 0
    
    def test_should_continue_processing(self):
        """Test processing continuation logic"""
        monitor = CostMonitor()
        
        # With normal usage, should continue
        monitor.usage_history = [
            {
                "timestamp": "2024-01-01T10:00:00",
                "tokens_used": 400,
                "cost": 0.0008,
                "idea_generated": True
            }
        ]
        
        assert monitor.should_continue_processing() is True
    
    def test_batch_cost_estimation(self):
        """Test batch processing cost estimation"""
        monitor = CostMonitor()
        monitor.usage_history = [
            {
                "timestamp": "2024-01-01T10:00:00",
                "tokens_used": 450,
                "cost": 0.0009,
                "idea_generated": True
            }
        ]
        
        estimate = monitor.estimate_batch_cost(10)
        
        assert estimate['complaint_count'] == 10
        assert estimate['estimated_tokens_per_complaint'] == 450
        assert estimate['total_estimated_tokens'] == 4500
        assert 'estimated_cost' in estimate
        assert 'can_afford' in estimate


def test_cost_guard_integration():
    """Integration test for cost guard with CI/CD"""
    monitor = CostMonitor()
    
    # This test should fail CI if the mean exceeds 600 tokens
    result = monitor.check_cost_guard()
    
    if not result['passed']:
        pytest.fail(
            f"Cost guard failed: Mean tokens per complaint ({result['mean_tokens_per_complaint']:.1f}) "
            f"exceeds threshold ({result['threshold']}). "
            f"This indicates the AI prompts or responses are too long and need optimization."
        )