"""
Unit tests for analysis engine.
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from analysis_engine import AnalysisEngine
from models import ChannelDetectionParams, KSTParams


class TestAnalysisEngine:
    """Test analysis engine functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engine = AnalysisEngine()
        self.sample_data = self._create_sample_data()
    
    def _create_sample_data(self, days=30):
        """Create sample OHLC data for testing."""
        dates = pd.date_range(start='2024-01-01', periods=days*24, freq='H')
        
        # Create trending data with some noise
        base_price = 18500
        trend = np.linspace(0, 1000, len(dates))
        noise = np.random.normal(0, 50, len(dates))
        prices = base_price + trend + noise
        
        data = []
        for i, (date, price) in enumerate(zip(dates, prices)):
            # Create OHLC with some variation
            high = price + np.random.uniform(0, 20)
            low = price - np.random.uniform(0, 20)
            open_price = price + np.random.uniform(-10, 10)
            close = price + np.random.uniform(-10, 10)
            volume = np.random.randint(1000, 10000)
            
            data.append({
                'timestamp': date,
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': volume
            })
        
        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        return df
    
    def test_detect_parallel_channel(self):
        """Test channel detection."""
        channel = self.engine.detect_parallel_channel(self.sample_data)
        
        assert isinstance(channel, Channel)
        assert hasattr(channel, 'valid')
        assert hasattr(channel, 'is_upward')
        assert hasattr(channel, 'touches_upper')
        assert hasattr(channel, 'touches_lower')
    
    def test_compute_kst(self):
        """Test KST indicator calculation."""
        kst_signal = self.engine.compute_kst(self.sample_data)
        
        assert hasattr(kst_signal, 'kst_value')
        assert hasattr(kst_signal, 'kst_signal')
        assert hasattr(kst_signal, 'crossover_direction')
        assert kst_signal.crossover_direction in ['bullish', 'bearish', 'none']
    
    def test_check_breakout_20m(self):
        """Test breakout detection."""
        # Create a simple channel
        channel = Channel(
            start_ts=datetime.now() - timedelta(days=7),
            end_ts=datetime.now(),
            upper_line={"slope": 0, "intercept": 19000},
            lower_line={"slope": 0, "intercept": 18000},
            touches_upper=3,
            touches_lower=3,
            is_upward=True,
            valid=True
        )
        
        # Create data with breakout
        breakout_data = self.sample_data.copy()
        breakout_data.iloc[-1, breakout_data.columns.get_loc('close')] = 19500  # Above upper line
        
        result = self.engine.check_breakout_20m(breakout_data, channel)
        assert result == "breakout_up"
    
    def test_compute_fibonacci_levels(self):
        """Test Fibonacci level calculation."""
        channel = Channel(
            start_ts=datetime.now() - timedelta(days=7),
            end_ts=datetime.now(),
            upper_line={"slope": 0, "intercept": 19000},
            lower_line={"slope": 0, "intercept": 18000},
            touches_upper=3,
            touches_lower=3,
            is_upward=True,
            valid=True
        )
        
        levels = self.engine.compute_fibonacci_levels(channel)
        
        assert "0.236" in levels
        assert "0.5" in levels
        assert "0.618" in levels
        
        # Test that levels are within expected range
        assert 18000 <= levels["0.236"] <= 19000
        assert 18000 <= levels["0.5"] <= 19000
        assert 18000 <= levels["0.618"] <= 19000
    
    def test_calculate_position_pnl(self):
        """Test position PnL calculation."""
        # Long position
        pnl_long = self.engine.calculate_position_pnl(100, 110, 10, "long")
        assert pnl_long == 100  # (110 - 100) * 10
        
        # Short position
        pnl_short = self.engine.calculate_position_pnl(100, 90, 10, "short")
        assert pnl_short == 100  # (100 - 90) * 10
        
        # Loss
        pnl_loss = self.engine.calculate_position_pnl(100, 90, 10, "long")
        assert pnl_loss == -100  # (90 - 100) * 10
    
    def test_should_exit_position(self):
        """Test position exit conditions."""
        position = {
            "entry_price": 100,
            "target_price": 120,
            "stop_loss_price": 80,
            "side": "long"
        }
        
        # Test target hit
        should_exit, reason = self.engine.should_exit_position(position, 125, None)
        assert should_exit == True
        assert reason == "target_hit"
        
        # Test stop loss hit
        should_exit, reason = self.engine.should_exit_position(position, 75, None)
        assert should_exit == True
        assert reason == "stop_loss"
        
        # Test no exit
        should_exit, reason = self.engine.should_exit_position(position, 105, None)
        assert should_exit == False
        assert reason == ""


if __name__ == "__main__":
    pytest.main([__file__])