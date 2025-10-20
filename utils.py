"""
Utility functions for the trading system.
"""
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from pathlib import Path
import pandas as pd
import numpy as np
from loguru import logger


def setup_logging(log_level: str = "INFO", log_dir: str = "logs") -> None:
    """Setup logging configuration with file rotation."""
    # Create logs directory if it doesn't exist
    Path(log_dir).mkdir(exist_ok=True)
    
    # Remove default handler
    logger.remove()
    
    # Add file handler with rotation
    logger.add(
        f"{log_dir}/strategy.log",
        rotation="10 MB",
        retention="30 days",
        level=log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}"
    )
    
    # Add console handler
    logger.add(
        lambda msg: print(msg, end=""),
        level=log_level,
        format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | {message}"
    )


def round_to_strike(price: float, strike_rounding: int = 100) -> int:
    """Round price to nearest strike."""
    return int(round(price / strike_rounding) * strike_rounding)


def get_nearest_strike(spot: float, strike_rounding: int = 100) -> int:
    """Get nearest ATM strike for given spot price."""
    return round_to_strike(spot, strike_rounding)


def is_trading_hours(current_time: datetime, start_time: str, end_time: str) -> bool:
    """Check if current time is within trading hours."""
    current = current_time.time()
    start = datetime.strptime(start_time, "%H:%M").time()
    end = datetime.strptime(end_time, "%H:%M").time()
    
    return start <= current <= end


def get_next_candle_time(current_time: datetime, candle_minutes: int) -> datetime:
    """Get the next candle close time."""
    # Round up to next candle boundary
    minutes_since_market_open = (current_time.hour - 9) * 60 + (current_time.minute - 15)
    next_candle_minutes = ((minutes_since_market_open // candle_minutes) + 1) * candle_minutes
    
    # Calculate next candle time
    market_open = current_time.replace(hour=9, minute=15, second=0, microsecond=0)
    next_candle = market_open + timedelta(minutes=next_candle_minutes)
    
    return next_candle


def safe_json_load(file_path: str, default: Any = None) -> Any:
    """Safely load JSON file with default fallback."""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def safe_json_save(data: Any, file_path: str) -> bool:
    """Safely save data to JSON file."""
    try:
        # Create directory if it doesn't exist
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        return True
    except Exception as e:
        logger.error(f"Failed to save JSON to {file_path}: {e}")
        return False


def calculate_percentage_change(old_value: float, new_value: float) -> float:
    """Calculate percentage change between two values."""
    if old_value == 0:
        return 0.0
    return ((new_value - old_value) / old_value) * 100


def format_currency(amount: float, currency: str = "₹") -> str:
    """Format currency amount with proper symbols."""
    return f"{currency}{amount:,.2f}"


def format_percentage(value: float, decimals: int = 2) -> str:
    """Format percentage with specified decimal places."""
    return f"{value:.{decimals}f}%"


def validate_dataframe(df: pd.DataFrame, required_columns: List[str]) -> bool:
    """Validate DataFrame has required columns and is not empty."""
    if df.empty:
        return False
    
    missing_columns = set(required_columns) - set(df.columns)
    if missing_columns:
        logger.warning(f"Missing columns: {missing_columns}")
        return False
    
    return True


def clean_ohlc_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and validate OHLC data."""
    # Remove rows with NaN values
    df = df.dropna()
    
    # Ensure numeric types
    numeric_columns = ['open', 'high', 'low', 'close', 'volume']
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Remove rows where OHLC data is invalid
    df = df.dropna(subset=numeric_columns)
    
    # Ensure high >= low and high/low >= open/close
    df = df[
        (df['high'] >= df['low']) &
        (df['high'] >= df['open']) &
        (df['high'] >= df['close']) &
        (df['low'] <= df['open']) &
        (df['low'] <= df['close'])
    ]
    
    return df


def get_cache_key(symbol: str, timeframe: str, start_date: str, end_date: str) -> str:
    """Generate cache key for data requests."""
    return f"{symbol}_{timeframe}_{start_date}_{end_date}"


def ensure_directory(path: str) -> None:
    """Ensure directory exists, create if it doesn't."""
    Path(path).mkdir(parents=True, exist_ok=True)


def get_timestamp() -> str:
    """Get current timestamp as string."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def calculate_fibonacci_levels(high: float, low: float) -> Dict[str, float]:
    """Calculate Fibonacci retracement levels."""
    diff = high - low
    
    return {
        "0.236": high - (diff * 0.236),
        "0.382": high - (diff * 0.382),
        "0.5": high - (diff * 0.5),
        "0.618": high - (diff * 0.618),
        "0.786": high - (diff * 0.786)
    }


def calculate_support_resistance(df: pd.DataFrame, window: int = 20) -> Dict[str, float]:
    """Calculate basic support and resistance levels."""
    if len(df) < window:
        return {"support": 0, "resistance": 0}
    
    recent_data = df.tail(window)
    
    # Simple support/resistance calculation
    support = recent_data['low'].min()
    resistance = recent_data['high'].max()
    
    return {
        "support": support,
        "resistance": resistance
    }