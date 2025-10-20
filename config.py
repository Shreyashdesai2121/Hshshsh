"""
Configuration management for the NIFTY50 trading system.
Uses Pydantic for type validation and environment variable loading.
"""
from typing import Optional, List
from pydantic import BaseSettings, Field
from datetime import time
import os


class Settings(BaseSettings):
    """Main configuration class for the trading system."""
    
    # Trading Mode
    mode: str = Field(default="dry_run", description="Trading mode: dry_run or live")
    run_strategy: bool = Field(default=False, description="Whether to run the strategy")
    one_trade_per_day: bool = Field(default=True, description="Limit to one trade per day")
    
    # Trading Hours
    trading_start: time = Field(default=time(9, 15), description="Trading start time")
    trading_end: time = Field(default=time(15, 30), description="Trading end time")
    
    # Risk Management
    slippage: float = Field(default=0.001, description="Slippage assumption (0.1%)")
    quantity: int = Field(default=1, description="Default quantity per trade")
    
    # Broker Selection
    use_dhan: bool = Field(default=True, description="Use Dhan as primary broker")
    use_zerodha: bool = Field(default=False, description="Use Zerodha as alternative broker")
    
    # API Keys - TODO: Replace with actual keys from .env file
    dhan_api_key: str = Field(default="", description="Dhan API key")
    dhan_api_secret: str = Field(default="", description="Dhan API secret")
    zerodha_api_key: str = Field(default="", description="Zerodha API key")
    zerodha_api_secret: str = Field(default="", description="Zerodha API secret")
    
    # Database
    database_url: str = Field(default="sqlite:///./trading_system.db", description="Database URL")
    
    # Dashboard
    dashboard_enabled: bool = Field(default=True, description="Enable dashboard")
    dashboard_port: int = Field(default=3000, description="Dashboard port")
    
    # Logging
    log_level: str = Field(default="INFO", description="Log level")
    
    # Strategy Parameters
    scheduler_candle_minutes: int = Field(default=20, description="Candle timeframe in minutes")
    nst_timeframe: str = Field(default="2h", description="No-Sure-Thing indicator timeframe")
    channel_min_days: int = Field(default=7, description="Minimum channel duration in days")
    channel_min_touches: int = Field(default=2, description="Minimum touches per channel line")
    profit_threshold_percent: float = Field(default=50.0, description="Profit threshold for target selection")
    
    # NIFTY50 Configuration
    nifty_symbol: str = Field(default="NIFTY50", description="Underlying symbol")
    strike_rounding: int = Field(default=100, description="Strike price rounding factor")
    
    # File Paths
    trades_dir: str = Field(default="trades", description="Directory for trade files")
    logs_dir: str = Field(default="logs", description="Directory for log files")
    state_file: str = Field(default="state.json", description="State persistence file")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()

# Validation
def validate_config():
    """Validate configuration settings."""
    if settings.mode not in ["dry_run", "live"]:
        raise ValueError("Mode must be 'dry_run' or 'live'")
    
    if settings.use_dhan and not settings.dhan_api_key:
        raise ValueError("Dhan API key required when USE_DHAN is True")
    
    if settings.use_zerodha and not settings.zerodha_api_key:
        raise ValueError("Zerodha API key required when USE_ZERODHA is True")
    
    if not settings.use_dhan and not settings.use_zerodha:
        raise ValueError("At least one broker must be enabled")


# Validate on import
validate_config()