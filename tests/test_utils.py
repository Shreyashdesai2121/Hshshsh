"""
Unit tests for utility functions.
"""
import pytest
from datetime import datetime
import pandas as pd
import numpy as np

from utils import (
    get_nearest_strike,
    round_to_strike,
    calculate_percentage_change,
    format_currency,
    format_percentage,
    calculate_fibonacci_levels,
    is_trading_hours
)


class TestStrikeCalculation:
    """Test strike calculation functions."""
    
    def test_get_nearest_strike(self):
        """Test nearest strike calculation."""
        assert get_nearest_strike(18500.0) == 18500
        assert get_nearest_strike(18525.0) == 18500
        assert get_nearest_strike(18575.0) == 18600
        assert get_nearest_strike(18550.0) == 18600
    
    def test_round_to_strike(self):
        """Test strike rounding."""
        assert round_to_strike(18500.0) == 18500
        assert round_to_strike(18525.0) == 18500
        assert round_to_strike(18575.0) == 18600
        assert round_to_strike(18550.0) == 18600


class TestFormatting:
    """Test formatting functions."""
    
    def test_calculate_percentage_change(self):
        """Test percentage change calculation."""
        assert calculate_percentage_change(100, 110) == 10.0
        assert calculate_percentage_change(100, 90) == -10.0
        assert calculate_percentage_change(0, 100) == 0.0
    
    def test_format_currency(self):
        """Test currency formatting."""
        assert format_currency(1234.56) == "₹1,234.56"
        assert format_currency(0) == "₹0.00"
        assert format_currency(-100) == "₹-100.00"
    
    def test_format_percentage(self):
        """Test percentage formatting."""
        assert format_percentage(10.5) == "10.50%"
        assert format_percentage(0) == "0.00%"
        assert format_percentage(-5.25, 1) == "-5.3%"


class TestFibonacci:
    """Test Fibonacci calculation."""
    
    def test_calculate_fibonacci_levels(self):
        """Test Fibonacci retracement levels."""
        levels = calculate_fibonacci_levels(100, 50)
        
        assert "0.236" in levels
        assert "0.5" in levels
        assert "0.618" in levels
        
        # Test 0.5 level
        assert abs(levels["0.5"] - 75.0) < 0.01
        
        # Test 0.236 level
        expected_236 = 100 - (50 * 0.236)
        assert abs(levels["0.236"] - expected_236) < 0.01


class TestTradingHours:
    """Test trading hours validation."""
    
    def test_is_trading_hours(self):
        """Test trading hours check."""
        # Test during trading hours
        trading_time = datetime(2024, 1, 15, 10, 30)  # 10:30 AM
        assert is_trading_hours(trading_time, "09:15", "15:30") == True
        
        # Test before trading hours
        early_time = datetime(2024, 1, 15, 8, 0)  # 8:00 AM
        assert is_trading_hours(early_time, "09:15", "15:30") == False
        
        # Test after trading hours
        late_time = datetime(2024, 1, 15, 16, 0)  # 4:00 PM
        assert is_trading_hours(late_time, "09:15", "15:30") == False


if __name__ == "__main__":
    pytest.main([__file__])