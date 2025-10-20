"""
Base broker adapter interface.
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Callable, Dict, Any
from datetime import datetime
import pandas as pd
from models import BrokerResponse, MarketData


class BrokerAdapter(ABC):
    """Abstract base class for broker adapters."""
    
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.authenticated = False
        self.session = None
    
    @abstractmethod
    async def authenticate(self) -> BrokerResponse:
        """Authenticate with the broker API."""
        pass
    
    @abstractmethod
    async def get_spot(self, symbol: str) -> BrokerResponse:
        """Get current spot price for symbol."""
        pass
    
    @abstractmethod
    async def get_option_instrument_token(
        self, 
        symbol: str, 
        strike: int, 
        option_type: str, 
        expiry: str
    ) -> BrokerResponse:
        """Get instrument token for option contract."""
        pass
    
    @abstractmethod
    async def fetch_ohlc(
        self, 
        instrument_token: str, 
        timeframe: str, 
        start: Optional[datetime] = None, 
        end: Optional[datetime] = None
    ) -> BrokerResponse:
        """Fetch OHLC data for instrument."""
        pass
    
    @abstractmethod
    async def subscribe_live_ticks(
        self, 
        instrument_tokens: List[str], 
        callback: Callable[[MarketData], None]
    ) -> BrokerResponse:
        """Subscribe to live tick data."""
        pass
    
    @abstractmethod
    async def place_order(
        self, 
        instrument_token: str, 
        qty: int, 
        order_type: str, 
        price: Optional[float] = None
    ) -> BrokerResponse:
        """Place an order."""
        pass
    
    @abstractmethod
    async def get_margin(self) -> BrokerResponse:
        """Get available margin."""
        pass
    
    @abstractmethod
    async def get_order_status(self, order_id: str) -> BrokerResponse:
        """Get order status."""
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str) -> BrokerResponse:
        """Cancel an order."""
        pass
    
    @abstractmethod
    async def get_positions(self) -> BrokerResponse:
        """Get current positions."""
        pass
    
    @abstractmethod
    async def close_position(self, position_id: str) -> BrokerResponse:
        """Close a specific position."""
        pass
    
    def is_authenticated(self) -> bool:
        """Check if adapter is authenticated."""
        return self.authenticated
    
    def get_session(self):
        """Get current session object."""
        return self.session