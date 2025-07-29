"""
Cost monitoring service for tracking AI API usage and enforcing limits
"""
import json
import statistics
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime, timedelta
from app.config import settings
from app.logging_config import logger


class CostMonitor:
    """Service for monitoring AI costs and enforcing usage limits"""
    
    def __init__(self):
        """Initialize cost monitor"""
        self.max_tokens_per_complaint = settings.max_tokens_per_complaint
        self.usage_history: List[Dict[str, Any]] = []
        self.cost_per_1k_tokens = 0.002  # GPT-3.5-turbo pricing
        self.daily_usage_limit = 100.0  # $100 daily limit
        self.sample_file = Path("sample_tokens.json")
        
        # Load historical usage if available
        self._load_usage_history()
        
        logger.info(f"Cost monitor initialized with {self.max_tokens_per_complaint} token limit per complaint")
    
    def _load_usage_history(self):
        """Load usage history from file if it exists"""
        try:
            if self.sample_file.exists():
                with open(self.sample_file, 'r') as f:
                    self.usage_history = json.load(f)
                logger.info(f"Loaded {len(self.usage_history)} usage records")
        except Exception as e:
            logger.warning(f"Could not load usage history: {str(e)}")
            self.usage_history = []
    
    def _save_usage_history(self):
        """Save usage history to file"""
        try:
            with open(self.sample_file, 'w') as f:
                json.dump(self.usage_history, f, indent=2, default=str)
            logger.debug("Usage history saved")
        except Exception as e:
            logger.error(f"Could not save usage history: {str(e)}")
    
    def record_usage(
        self, 
        complaint_text: str, 
        tokens_used: int, 
        cost: float,
        idea_generated: bool = True
    ):
        """
        Record API usage for monitoring
        
        Args:
            complaint_text: The complaint text processed
            tokens_used: Number of tokens consumed
            cost: Cost in USD
            idea_generated: Whether idea was successfully generated
        """
        usage_record = {
            'timestamp': datetime.utcnow().isoformat(),
            'complaint_length': len(complaint_text),
            'tokens_used': tokens_used,
            'cost': cost,
            'idea_generated': idea_generated,
            'tokens_per_char': tokens_used / len(complaint_text) if complaint_text else 0
        }
        
        self.usage_history.append(usage_record)
        
        # Keep only last 1000 records to avoid memory issues
        if len(self.usage_history) > 1000:
            self.usage_history = self.usage_history[-1000:]
        
        self._save_usage_history()
        
        logger.debug(f"Recorded usage: {tokens_used} tokens, ${cost:.4f}")
    
    def get_mean_tokens_per_complaint(self, days: int = 7) -> float:
        """
        Get mean tokens per complaint over specified days
        
        Args:
            days: Number of days to look back
            
        Returns:
            Mean tokens per complaint
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        recent_usage = [
            record for record in self.usage_history
            if datetime.fromisoformat(record['timestamp']) > cutoff_date
            and record['idea_generated']  # Only count successful generations
        ]
        
        if not recent_usage:
            return 0.0
        
        tokens_list = [record['tokens_used'] for record in recent_usage]
        mean_tokens = statistics.mean(tokens_list)
        
        logger.info(f"Mean tokens per complaint (last {days} days): {mean_tokens:.1f}")
        return mean_tokens
    
    def check_cost_guard(self, days: int = 7) -> Dict[str, Any]:
        """
        Check if cost guard thresholds are exceeded
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dictionary with cost guard results
        """
        mean_tokens = self.get_mean_tokens_per_complaint(days)
        
        # Check against threshold
        threshold_exceeded = mean_tokens > self.max_tokens_per_complaint
        
        # Calculate other metrics
        total_cost = self.get_total_cost(days)
        total_requests = len([
            r for r in self.usage_history
            if datetime.fromisoformat(r['timestamp']) > datetime.utcnow() - timedelta(days=days)
        ])
        
        result = {
            'passed': not threshold_exceeded,
            'mean_tokens_per_complaint': mean_tokens,
            'threshold': self.max_tokens_per_complaint,
            'threshold_exceeded': threshold_exceeded,
            'total_cost_period': total_cost,
            'total_requests_period': total_requests,
            'period_days': days,
            'check_timestamp': datetime.utcnow().isoformat()
        }
        
        if threshold_exceeded:
            logger.error(
                f"Cost guard FAILED: Mean tokens ({mean_tokens:.1f}) exceeds threshold ({self.max_tokens_per_complaint})"
            )
        else:
            logger.info(
                f"Cost guard PASSED: Mean tokens ({mean_tokens:.1f}) within threshold ({self.max_tokens_per_complaint})"
            )
        
        return result
    
    def get_total_cost(self, days: int = 1) -> float:
        """
        Get total cost over specified period
        
        Args:
            days: Number of days to look back
            
        Returns:
            Total cost in USD
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        recent_usage = [
            record for record in self.usage_history
            if datetime.fromisoformat(record['timestamp']) > cutoff_date
        ]
        
        total_cost = sum(record['cost'] for record in recent_usage)
        return total_cost
    
    def check_daily_limit(self) -> Dict[str, Any]:
        """
        Check if daily spending limit is exceeded
        
        Returns:
            Dictionary with daily limit check results
        """
        daily_cost = self.get_total_cost(days=1)
        limit_exceeded = daily_cost > self.daily_usage_limit
        
        result = {
            'daily_cost': daily_cost,
            'daily_limit': self.daily_usage_limit,
            'limit_exceeded': limit_exceeded,
            'remaining_budget': max(0, self.daily_usage_limit - daily_cost),
            'check_timestamp': datetime.utcnow().isoformat()
        }
        
        if limit_exceeded:
            logger.warning(f"Daily cost limit exceeded: ${daily_cost:.2f} > ${self.daily_usage_limit}")
        
        return result
    
    def get_usage_statistics(self, days: int = 7) -> Dict[str, Any]:
        """
        Get comprehensive usage statistics
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dictionary with usage statistics
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        recent_usage = [
            record for record in self.usage_history
            if datetime.fromisoformat(record['timestamp']) > cutoff_date
        ]
        
        if not recent_usage:
            return {
                'period_days': days,
                'total_requests': 0,
                'successful_requests': 0,
                'total_cost': 0.0,
                'mean_tokens': 0.0,
                'median_tokens': 0.0,
                'min_tokens': 0,
                'max_tokens': 0
            }
        
        successful_usage = [r for r in recent_usage if r['idea_generated']]
        tokens_list = [r['tokens_used'] for r in successful_usage]
        
        stats = {
            'period_days': days,
            'total_requests': len(recent_usage),
            'successful_requests': len(successful_usage),
            'failed_requests': len(recent_usage) - len(successful_usage),
            'success_rate': len(successful_usage) / len(recent_usage) if recent_usage else 0,
            'total_cost': sum(r['cost'] for r in recent_usage),
            'total_tokens': sum(r['tokens_used'] for r in recent_usage),
            'mean_tokens': statistics.mean(tokens_list) if tokens_list else 0,
            'median_tokens': statistics.median(tokens_list) if tokens_list else 0,
            'min_tokens': min(tokens_list) if tokens_list else 0,
            'max_tokens': max(tokens_list) if tokens_list else 0,
            'tokens_std_dev': statistics.stdev(tokens_list) if len(tokens_list) > 1 else 0
        }
        
        return stats
    
    def should_continue_processing(self) -> bool:
        """
        Check if processing should continue based on cost limits
        
        Returns:
            True if processing should continue
        """
        # Check daily limit
        daily_check = self.check_daily_limit()
        if daily_check['limit_exceeded']:
            logger.error("Daily cost limit exceeded, stopping processing")
            return False
        
        # Check cost guard
        cost_guard = self.check_cost_guard()
        if not cost_guard['passed']:
            logger.error("Cost guard threshold exceeded, stopping processing")
            return False
        
        return True
    
    def estimate_batch_cost(self, complaint_count: int) -> Dict[str, Any]:
        """
        Estimate cost for processing a batch of complaints
        
        Args:
            complaint_count: Number of complaints to process
            
        Returns:
            Dictionary with cost estimation
        """
        mean_tokens = self.get_mean_tokens_per_complaint()
        
        # Use historical average or default estimate
        estimated_tokens_per_complaint = mean_tokens if mean_tokens > 0 else 400
        
        total_estimated_tokens = complaint_count * estimated_tokens_per_complaint
        estimated_cost = (total_estimated_tokens / 1000) * self.cost_per_1k_tokens
        
        current_daily_cost = self.get_total_cost(days=1)
        remaining_budget = max(0, self.daily_usage_limit - current_daily_cost)
        
        can_afford = estimated_cost <= remaining_budget
        
        return {
            'complaint_count': complaint_count,
            'estimated_tokens_per_complaint': estimated_tokens_per_complaint,
            'total_estimated_tokens': total_estimated_tokens,
            'estimated_cost': estimated_cost,
            'current_daily_cost': current_daily_cost,
            'remaining_budget': remaining_budget,
            'can_afford': can_afford,
            'max_affordable_complaints': int(remaining_budget / (estimated_tokens_per_complaint / 1000 * self.cost_per_1k_tokens)) if estimated_tokens_per_complaint > 0 else 0
        }
    
    def clear_usage_history(self):
        """Clear all usage history"""
        self.usage_history = []
        self._save_usage_history()
        logger.info("Usage history cleared")
    
    def export_usage_data(self, filepath: str):
        """
        Export usage data to JSON file
        
        Args:
            filepath: Path to export file
        """
        try:
            with open(filepath, 'w') as f:
                json.dump(self.usage_history, f, indent=2, default=str)
            logger.info(f"Usage data exported to {filepath}")
        except Exception as e:
            logger.error(f"Failed to export usage data: {str(e)}")
            raise