"""
Data engine for fetching and managing market data.
"""
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import json
from loguru import logger

from config import settings
from broker import DhanAdapter, ZerodhaAdapter
from utils import get_nearest_strike, safe_json_save, safe_json_load, get_cache_key, clean_ohlc_data


class DataEngine:
    """Data engine for fetching and caching market data."""
    
    def __init__(self):
        self.broker = None
        self.cache_dir = Path("cache")
        self.cache_dir.mkdir(exist_ok=True)
        self._initialize_broker()
    
    def _initialize_broker(self):
        """Initialize the appropriate broker adapter."""
        try:
            if settings.use_dhan:
                self.broker = DhanAdapter(settings.dhan_api_key, settings.dhan_api_secret)
                logger.info("Initialized Dhan adapter")
            elif settings.use_zerodha:
                self.broker = ZerodhaAdapter(settings.zerodha_api_key, settings.zerodha_api_secret)
                logger.info("Initialized Zerodha adapter")
            else:
                raise ValueError("No broker configured")
        except Exception as e:
            logger.error(f"Failed to initialize broker: {e}")
            raise
    
    async def authenticate(self) -> bool:
        """Authenticate with the broker."""
        try:
            response = await self.broker.authenticate()
            if response.success:
                logger.info("Successfully authenticated with broker")
                return True
            else:
                logger.error(f"Authentication failed: {response.error}")
                return False
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False
    
    async def get_nifty_spot(self) -> float:
        """Get current NIFTY50 spot price."""
        try:
            response = await self.broker.get_spot(settings.nifty_symbol)
            if response.success:
                spot_price = response.data.get("price", 0.0)
                logger.debug(f"NIFTY50 spot price: {spot_price}")
                return spot_price
            else:
                logger.error(f"Failed to get spot price: {response.error}")
                return 0.0
        except Exception as e:
            logger.error(f"Error getting spot price: {e}")
            return 0.0
    
    def get_nearest_strike(self, spot: float) -> int:
        """Get nearest ATM strike for given spot price."""
        return get_nearest_strike(spot, settings.strike_rounding)
    
    async def get_option_instrument_token(
        self, 
        strike: int, 
        option_type: str, 
        expiry: str
    ) -> Optional[str]:
        """Get instrument token for option contract."""
        try:
            response = await self.broker.get_option_instrument_token(
                settings.nifty_symbol, strike, option_type, expiry
            )
            if response.success:
                return response.data.get("instrument_token")
            else:
                logger.error(f"Failed to get instrument token: {response.error}")
                return None
        except Exception as e:
            logger.error(f"Error getting instrument token: {e}")
            return None
    
    def _get_cache_file(self, cache_key: str) -> Path:
        """Get cache file path for given key."""
        return self.cache_dir / f"{cache_key}.json"
    
    def _load_from_cache(self, cache_key: str) -> Optional[pd.DataFrame]:
        """Load data from cache."""
        try:
            cache_file = self._get_cache_file(cache_key)
            if cache_file.exists():
                data = safe_json_load(str(cache_file))
                if data:
                    df = pd.DataFrame(data)
                    if not df.empty:
                        df['timestamp'] = pd.to_datetime(df['timestamp'])
                        df = df.set_index('timestamp')
                        return df
        except Exception as e:
            logger.warning(f"Failed to load from cache: {e}")
        return None
    
    def _save_to_cache(self, cache_key: str, df: pd.DataFrame) -> bool:
        """Save data to cache."""
        try:
            cache_file = self._get_cache_file(cache_key)
            data = df.reset_index().to_dict('records')
            return safe_json_save(data, str(cache_file))
        except Exception as e:
            logger.warning(f"Failed to save to cache: {e}")
            return False
    
    async def fetch_ohlc_data(
        self, 
        instrument_token: str, 
        timeframe: str, 
        start_date: datetime, 
        end_date: datetime,
        use_cache: bool = True
    ) -> pd.DataFrame:
        """Fetch OHLC data for instrument with caching."""
        try:
            # Generate cache key
            cache_key = get_cache_key(
                instrument_token, 
                timeframe, 
                start_date.strftime("%Y-%m-%d"), 
                end_date.strftime("%Y-%m-%d")
            )
            
            # Try to load from cache first
            if use_cache:
                cached_data = self._load_from_cache(cache_key)
                if cached_data is not None:
                    logger.debug(f"Loaded data from cache: {cache_key}")
                    return cached_data
            
            # Fetch from broker
            response = await self.broker.fetch_ohlc(
                instrument_token, timeframe, start_date, end_date
            )
            
            if response.success:
                df = response.data
                if df is not None and not df.empty:
                    # Clean the data
                    df = clean_ohlc_data(df)
                    
                    # Save to cache
                    if use_cache:
                        self._save_to_cache(cache_key, df)
                    
                    logger.debug(f"Fetched {len(df)} candles for {instrument_token}")
                    return df
                else:
                    logger.warning(f"No data returned for {instrument_token}")
                    return pd.DataFrame()
            else:
                logger.error(f"Failed to fetch OHLC data: {response.error}")
                return pd.DataFrame()
        
        except Exception as e:
            logger.error(f"Error fetching OHLC data: {e}")
            return pd.DataFrame()
    
    async def get_call_put_data(
        self, 
        strike: int, 
        lookback_days: int = 30
    ) -> Dict[str, Dict[str, pd.DataFrame]]:
        """Get 20-minute and 2-hour data for both CE and PE options."""
        try:
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=lookback_days)
            
            # Get current expiry (simplified - in production, get from broker)
            expiry = self._get_current_expiry()
            
            # Get instrument tokens
            call_token = await self.get_option_instrument_token(strike, "CE", expiry)
            put_token = await self.get_option_instrument_token(strike, "PE", expiry)
            
            if not call_token or not put_token:
                logger.error("Failed to get instrument tokens")
                return {}
            
            # Fetch data for both timeframes
            data = {}
            
            for option_type, token in [("CE", call_token), ("PE", put_token)]:
                data[option_type] = {}
                
                # 20-minute data
                df_20m = await self.fetch_ohlc_data(
                    token, "20min", start_date, end_date
                )
                data[option_type]["20min"] = df_20m
                
                # 2-hour data
                df_2h = await self.fetch_ohlc_data(
                    token, "2h", start_date, end_date
                )
                data[option_type]["2h"] = df_2h
                
                logger.info(f"Fetched data for {option_type} {strike}: {len(df_20m)} 20m candles, {len(df_2h)} 2h candles")
            
            return data
        
        except Exception as e:
            logger.error(f"Error getting call/put data: {e}")
            return {}
    
    def _get_current_expiry(self) -> str:
        """Get current expiry date for NIFTY options."""
        # TODO: Implement proper expiry calculation
        # For now, return a placeholder
        # In production, this should fetch from broker or use a proper calculation
        today = datetime.now()
        # Simple logic: find next Thursday
        days_ahead = 3 - today.weekday()  # Thursday is 3
        if days_ahead <= 0:
            days_ahead += 7
        next_thursday = today + timedelta(days=days_ahead)
        return next_thursday.strftime("%Y-%m-%d")
    
    async def get_live_price(self, instrument_token: str) -> float:
        """Get live price for instrument."""
        try:
            # TODO: Implement live price fetching
            # For now, return a placeholder
            return 0.0
        except Exception as e:
            logger.error(f"Error getting live price: {e}")
            return 0.0
    
    def validate_data_quality(self, df: pd.DataFrame, min_candles: int = 100) -> bool:
        """Validate data quality for analysis."""
        if df.empty:
            return False
        
        if len(df) < min_candles:
            logger.warning(f"Insufficient data: {len(df)} candles (minimum: {min_candles})")
            return False
        
        # Check for missing values
        if df.isnull().any().any():
            logger.warning("Data contains missing values")
            return False
        
        # Check for zero or negative prices
        if (df[['open', 'high', 'low', 'close']] <= 0).any().any():
            logger.warning("Data contains zero or negative prices")
            return False
        
        # Check for reasonable price movements
        price_changes = df['close'].pct_change().abs()
        if (price_changes > 0.1).any():  # 10% change in single candle
            logger.warning("Data contains extreme price movements")
            return False
        
        return True
    
    async def get_market_status(self) -> Dict[str, Any]:
        """Get current market status."""
        try:
            # TODO: Implement market status checking
            # For now, return a placeholder
            return {
                "is_open": True,
                "next_open": None,
                "next_close": None
            }
        except Exception as e:
            logger.error(f"Error getting market status: {e}")
            return {"is_open": False, "error": str(e)}
    
    def clear_cache(self) -> bool:
        """Clear all cached data."""
        try:
            import shutil
            if self.cache_dir.exists():
                shutil.rmtree(self.cache_dir)
                self.cache_dir.mkdir(exist_ok=True)
            logger.info("Cache cleared successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return False
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            cache_files = list(self.cache_dir.glob("*.json"))
            total_size = sum(f.stat().st_size for f in cache_files)
            
            return {
                "file_count": len(cache_files),
                "total_size_mb": total_size / (1024 * 1024),
                "cache_dir": str(self.cache_dir)
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {"error": str(e)}


# Global data engine instance
data_engine = DataEngine()