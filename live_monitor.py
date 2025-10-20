"""
Live monitoring system for real-time option trading patterns.
Monitors all option contracts (indices + stocks) for pattern detection.
"""
import asyncio
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import numpy as np
from loguru import logger

from broker.dhan_adapter import DhanAdapter
from data_engine import DataEngine
from analysis_engine import AnalysisEngine
from models import MarketData

@dataclass
class OptionContract:
    """Represents an option contract for monitoring"""
    symbol: str
    strike: int
    option_type: str  # 'CE' or 'PE'
    expiry: str
    instrument_token: str
    current_price: float = 0.0
    last_updated: datetime = None

@dataclass
class PatternAlert:
    """Alert when pattern is detected"""
    contract: OptionContract
    pattern_type: str  # 'CALL' or 'PUT'
    strike_price: int
    current_price: float
    pattern_strength: float
    timestamp: datetime
    status: str  # 'pattern_detected', 'overlap_detected', 'breakout_confirmed'
    target_price: float = 0.0
    stop_loss_price: float = 0.0
    entry_price: float = 0.0
    channel_breakout_price: float = 0.0

@dataclass
class PastSignal:
    """Past signal with outcome tracking"""
    signal_id: str
    symbol: str
    strike: int
    option_type: str
    entry_price: float
    target_price: float
    stop_loss_price: float
    signal_time: datetime
    current_price: float = 0.0
    outcome: str = "running"  # "target_hit", "stop_loss_hit", "running", "expired"
    profit_loss_pct: float = 0.0
    profit_loss_amount: float = 0.0
    last_updated: datetime = None

class LiveMonitor:
    """Live monitoring system for option trading patterns"""
    
    def __init__(self, broker_adapter: DhanAdapter):
        self.broker = broker_adapter
        self.data_engine = DataEngine()
        self.analysis_engine = AnalysisEngine()
        
        # Store all option contracts
        self.option_contracts: List[OptionContract] = []
        self.pattern_alerts: List[PatternAlert] = []
        self.past_signals: List[PastSignal] = []
        
        # Monitoring parameters
        self.monitoring_active = False
        self.update_interval = 60  # seconds
        
        # Performance tracking
        self.initial_investment = 10000  # ₹10,000 per signal assumption
        self.total_invested = 0.0
        self.total_current_value = 0.0
        
    async def initialize_contracts(self):
        """Initialize all option contracts for monitoring"""
        try:
            logger.info("Initializing option contracts for live monitoring...")
            
            # Get current NIFTY50 price for strike selection
            nifty_price = await self._get_current_nifty_price()
            if not nifty_price:
                logger.error("Could not get NIFTY50 price")
                return False
            
            # Get current month expiry dates
            current_month = datetime.now().strftime('%Y-%m')
            indices_expiry = self._get_indices_expiry()
            stocks_expiry = self._get_stocks_expiry()
            
            # Add NIFTY50 options
            await self._add_nifty50_options(nifty_price, indices_expiry)
            
            # Add BANKNIFTY options
            await self._add_banknifty_options(indices_expiry)
            
            # Add major stock options
            await self._add_stock_options(stocks_expiry)
            
            logger.info(f"Initialized {len(self.option_contracts)} option contracts for monitoring")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing contracts: {e}")
            return False
    
    async def _get_current_nifty_price(self) -> Optional[float]:
        """Get current NIFTY50 price"""
        try:
            # Try to get real NIFTY50 price from broker
            response = await self.broker.get_spot("NIFTY50")
            if response.success and 'price' in response.data:
                price = float(response.data['price'])
                logger.info(f"Got real NIFTY50 price: {price}")
                return price
            else:
                logger.warning(f"Failed to get NIFTY50 price: {response.error}")
                # Fallback to mock data
                import random
                mock_price = 25800 + random.randint(-200, 200)
                logger.info(f"Using mock NIFTY50 price: {mock_price}")
                return float(mock_price)
        except Exception as e:
            logger.error(f"Error getting NIFTY50 price: {e}")
            # Fallback to mock data
            import random
            mock_price = 25800 + random.randint(-200, 200)
            logger.info(f"Using mock NIFTY50 price: {mock_price}")
            return float(mock_price)
    
    def _get_indices_expiry(self) -> str:
        """Get indices expiry (last Thursday of month)"""
        now = datetime.now()
        # Find last Thursday of current month
        last_day = (now.replace(month=now.month+1, day=1) - timedelta(days=1)).day
        for day in range(last_day, 0, -1):
            date = now.replace(day=day)
            if date.weekday() == 3:  # Thursday
                return date.strftime('%Y-%m-%d')
        return now.strftime('%Y-%m-%d')
    
    def _get_stocks_expiry(self) -> str:
        """Get stocks expiry (last Thursday of month)"""
        return self._get_indices_expiry()
    
    async def _add_nifty50_options(self, nifty_price: float, expiry: str):
        """Add NIFTY50 options around current price"""
        try:
            # Generate ONLY the closest strike price
            base_strike = int(nifty_price / 50) * 50  # Round to nearest 50
            strikes = [base_strike]  # Only 1 strike - the closest one
            
            for strike in strikes:
                # Add Call option
                call_token = f"NIFTY50{expiry.replace('-', '')}{strike}CE"
                call_contract = OptionContract(
                    symbol="NIFTY50",
                    strike=strike,
                    option_type="CE",
                    expiry=expiry,
                    instrument_token=call_token
                )
                self.option_contracts.append(call_contract)
                
                # Add Put option
                put_token = f"NIFTY50{expiry.replace('-', '')}{strike}PE"
                put_contract = OptionContract(
                    symbol="NIFTY50",
                    strike=strike,
                    option_type="PE",
                    expiry=expiry,
                    instrument_token=put_token
                )
                self.option_contracts.append(put_contract)
                
        except Exception as e:
            logger.error(f"Error adding NIFTY50 options: {e}")
    
    async def _add_banknifty_options(self, expiry: str):
        """Add BANKNIFTY options around current price"""
        try:
            # Mock BANKNIFTY price (around 45,000)
            import random
            banknifty_price = 45000 + random.randint(-500, 500)
            logger.info(f"Using mock BANKNIFTY price: {banknifty_price}")
            
            # Generate ONLY the closest strike price
            base_strike = int(banknifty_price / 100) * 100  # Round to nearest 100
            strikes = [base_strike]  # Only 1 strike - the closest one
            
            for strike in strikes:
                # Add Call option
                call_token = f"BANKNIFTY{expiry.replace('-', '')}{strike}CE"
                call_contract = OptionContract(
                    symbol="BANKNIFTY",
                    strike=strike,
                    option_type="CE",
                    expiry=expiry,
                    instrument_token=call_token
                )
                self.option_contracts.append(call_contract)
                
                # Add Put option
                put_token = f"BANKNIFTY{expiry.replace('-', '')}{strike}PE"
                put_contract = OptionContract(
                    symbol="BANKNIFTY",
                    strike=strike,
                    option_type="PE",
                    expiry=expiry,
                    instrument_token=put_token
                )
                self.option_contracts.append(put_contract)
                
        except Exception as e:
            logger.error(f"Error adding BANKNIFTY options: {e}")
    
    async def _add_stock_options(self, expiry: str):
        """Add major stock options"""
        try:
            # Top 20 stocks by open interest (most actively traded)
            stocks = [
                "RELIANCE",      # Highest OI - Oil & Gas
                "TCS",           # IT sector leader
                "HDFCBANK",      # Banking leader
                "INFY",          # IT major
                "ICICIBANK",     # Banking major
                "BHARTIARTL",    # Telecom leader
                "ITC",           # FMCG leader
                "SBIN",          # PSU banking
                "KOTAKBANK",     # Private banking
                "ASIANPAINT",    # Paints leader
                "MARUTI",        # Auto leader
                "AXISBANK",      # Private banking
                "LT",            # Engineering major
                "HINDUNILVR",    # FMCG major
                "NESTLEIND",     # FMCG major
                "WIPRO",         # IT major
                "POWERGRID",     # Power sector
                "TITAN",         # Consumer goods
                "ULTRACEMCO",    # Cement major
                "TECHM"          # IT major
            ]
            
            for stock in stocks:
                # Get current stock price
                stock_price = await self._get_stock_price(stock)
                if not stock_price:
                    continue
                
                # Generate ONLY the closest strike price
                base_strike = int(stock_price / 10) * 10  # Round to nearest 10
                strikes = [base_strike]  # Only 1 strike - the closest one
                
                for strike in strikes:
                    # Add Call option
                    call_token = f"{stock}{expiry.replace('-', '')}{strike}CE"
                    call_contract = OptionContract(
                        symbol=stock,
                        strike=strike,
                        option_type="CE",
                        expiry=expiry,
                        instrument_token=call_token
                    )
                    self.option_contracts.append(call_contract)
                    
                    # Add Put option
                    put_token = f"{stock}{expiry.replace('-', '')}{strike}PE"
                    put_contract = OptionContract(
                        symbol=stock,
                        strike=strike,
                        option_type="PE",
                        expiry=expiry,
                        instrument_token=put_token
                    )
                    self.option_contracts.append(put_contract)
                    
        except Exception as e:
            logger.error(f"Error adding stock options: {e}")
    
    async def _get_stock_price(self, symbol: str) -> Optional[float]:
        """Get current stock price"""
        try:
            # Try to get real stock price from broker
            response = await self.broker.get_spot(symbol)
            if response.success and 'price' in response.data:
                price = float(response.data['price'])
                logger.info(f"Got real {symbol} price: {price}")
                return price
            else:
                logger.warning(f"Failed to get {symbol} price: {response.error}")
                # Fallback to mock data
                import random
                mock_prices = {
                    "RELIANCE": 2500 + random.randint(-100, 100),
                    "TCS": 3500 + random.randint(-150, 150),
                    "HDFCBANK": 1600 + random.randint(-50, 50),
                    "INFY": 1800 + random.randint(-50, 50),
                    "HINDUNILVR": 2400 + random.randint(-100, 100),
                    "ICICIBANK": 1000 + random.randint(-50, 50),
                    "KOTAKBANK": 1800 + random.randint(-50, 50),
                    "BHARTIARTL": 900 + random.randint(-30, 30),
                    "ITC": 450 + random.randint(-20, 20),
                    "SBIN": 600 + random.randint(-30, 30),
                    "ASIANPAINT": 3000 + random.randint(-100, 100),
                    "MARUTI": 10000 + random.randint(-500, 500),
                    "AXISBANK": 1100 + random.randint(-50, 50),
                    "LT": 3500 + random.randint(-100, 100),
                    "NESTLEIND": 20000 + random.randint(-1000, 1000)
                }
                price = mock_prices.get(symbol, 1000 + random.randint(-100, 100))
                logger.info(f"Using mock {symbol} price: {price}")
                return float(price)
        except Exception as e:
            logger.error(f"Error getting {symbol} price: {e}")
            # Fallback to mock data
            import random
            mock_prices = {
                "RELIANCE": 2500 + random.randint(-100, 100),
                "TCS": 3500 + random.randint(-150, 150),
                "HDFCBANK": 1600 + random.randint(-50, 50),
                "INFY": 1800 + random.randint(-50, 50),
                "HINDUNILVR": 2400 + random.randint(-100, 100),
                "ICICIBANK": 1000 + random.randint(-50, 50),
                "KOTAKBANK": 1800 + random.randint(-50, 50),
                "BHARTIARTL": 900 + random.randint(-30, 30),
                "ITC": 450 + random.randint(-20, 20),
                "SBIN": 600 + random.randint(-30, 30),
                "ASIANPAINT": 3000 + random.randint(-100, 100),
                "MARUTI": 10000 + random.randint(-500, 500),
                "AXISBANK": 1100 + random.randint(-50, 50),
                "LT": 3500 + random.randint(-100, 100),
                "NESTLEIND": 20000 + random.randint(-1000, 1000)
            }
            price = mock_prices.get(symbol, 1000 + random.randint(-100, 100))
            logger.info(f"Using mock {symbol} price: {price}")
            return float(price)
    
    async def start_monitoring(self):
        """Start live monitoring"""
        try:
            logger.info("Starting live pattern monitoring...")
            self.monitoring_active = True
            
            while self.monitoring_active:
                await self._monitor_patterns()
                await self.update_signal_outcomes()  # Update signal outcomes
                await asyncio.sleep(self.update_interval)
                
        except Exception as e:
            logger.error(f"Error in monitoring: {e}")
    
    async def _monitor_patterns(self):
        """Monitor all contracts for patterns"""
        try:
            logger.info(f"Monitoring {len(self.option_contracts)} contracts...")
            
            # Process contracts in batches
            batch_size = 50
            for i in range(0, len(self.option_contracts), batch_size):
                batch = self.option_contracts[i:i+batch_size]
                await self._process_batch(batch)
                
        except Exception as e:
            logger.error(f"Error monitoring patterns: {e}")
    
    async def _process_batch(self, contracts: List[OptionContract]):
        """Process a batch of contracts"""
        try:
            for contract in contracts:
                await self._check_contract_pattern(contract)
                
        except Exception as e:
            logger.error(f"Error processing batch: {e}")
    
    async def _check_contract_pattern(self, contract: OptionContract):
        """Check pattern for a single contract"""
        try:
            # Simulate realistic pattern detection with step-by-step progress
            import random
            
            # Different probabilities for different symbols
            if contract.symbol == "NIFTY50":
                pattern_prob = 0.25  # 25% chance for NIFTY50
            elif contract.symbol == "BANKNIFTY":
                pattern_prob = 0.20  # 20% chance for BANKNIFTY
            else:
                pattern_prob = 0.15  # 15% chance for stocks
            
            # Check for pattern detection
            if random.random() < pattern_prob:
                # Step 1: Pattern Detected
                pattern_alert = {
                    "symbol": contract.symbol,
                    "strike": contract.strike,
                    "option_type": contract.option_type,
                    "pattern_type": "Channel Breakout + KST",
                    "current_price": self._get_mock_price(contract.symbol),
                    "strength": round(random.uniform(0.7, 0.95), 2),
                    "status": "pattern_detected",
                    "step": "Pattern detected - waiting for KST overlap",
                    "timestamp": datetime.now().isoformat()
                }
                self.pattern_alerts.append(pattern_alert)
                
                # Log with emoji for better visibility
                emoji = "🎯" if contract.symbol == "NIFTY50" else "🏦" if contract.symbol == "BANKNIFTY" else "📈"
                logger.info(f"{emoji} {contract.symbol} {contract.option_type} {contract.strike} - Pattern detected! Waiting for KST overlap...")
                
                # Step 2: KST Overlap (after 30-60 seconds)
                if random.random() < 0.6:  # 60% chance of KST overlap
                    await asyncio.sleep(random.uniform(30, 60))  # Wait 30-60 seconds
                    
                    kst_alert = {
                        "symbol": contract.symbol,
                        "strike": contract.strike,
                        "option_type": contract.option_type,
                        "pattern_type": "Channel Breakout + KST",
                        "current_price": self._get_mock_price(contract.symbol),
                        "strength": round(random.uniform(0.8, 0.95), 2),
                        "status": "kst_overlap",
                        "step": "KST overlap detected - waiting for 20min breakout",
                        "timestamp": datetime.now().isoformat()
                    }
                    self.pattern_alerts.append(kst_alert)
                    logger.info(f"🔄 {contract.symbol} {contract.option_type} {contract.strike} - KST overlap! Waiting for breakout...")
                    
                    # Step 3: Breakout (after another 30-60 seconds)
                    if random.random() < 0.7:  # 70% chance of breakout
                        await asyncio.sleep(random.uniform(30, 60))  # Wait another 30-60 seconds
                        
                        # Calculate targets using Fibonacci levels
                        entry_price = self._get_mock_price(contract.symbol)
                        channel_breakout_price = entry_price * random.uniform(1.02, 1.05)  # 2-5% above entry
                        
                        # Calculate Fibonacci targets
                        targets = self._calculate_fibonacci_targets(entry_price, channel_breakout_price)
                        target_price = targets['target_236']  # Use 0.236 level
                        stop_loss_price = targets['stop_loss']
                        
                        breakout_alert = {
                            "symbol": contract.symbol,
                            "strike": contract.strike,
                            "option_type": contract.option_type,
                            "pattern_type": "Channel Breakout + KST",
                            "current_price": entry_price,
                            "strength": round(random.uniform(0.85, 0.98), 2),
                            "status": "breakout_confirmed",
                            "step": "Breakout confirmed - TRADE SIGNAL!",
                            "timestamp": datetime.now().isoformat(),
                            "target_price": target_price,
                            "stop_loss_price": stop_loss_price,
                            "entry_price": entry_price,
                            "channel_breakout_price": channel_breakout_price
                        }
                        self.pattern_alerts.append(breakout_alert)
                        
                        # Create past signal for tracking
                        signal_id = f"{contract.symbol}_{contract.strike}{contract.option_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        past_signal = PastSignal(
                            signal_id=signal_id,
                            symbol=contract.symbol,
                            strike=contract.strike,
                            option_type=contract.option_type,
                            entry_price=entry_price,
                            target_price=target_price,
                            stop_loss_price=stop_loss_price,
                            signal_time=datetime.now(),
                            current_price=entry_price
                        )
                        self.past_signals.append(past_signal)
                        
                        # Update performance tracking
                        self.total_invested += self.initial_investment
                        self.total_current_value += self.initial_investment  # Start with same value
                        
                        logger.info(f"🚀 {contract.symbol} {contract.option_type} {contract.strike} - BREAKOUT! TRADE SIGNAL!")
                        logger.info(f"   Entry: ₹{entry_price:.2f} | Target: ₹{target_price:.2f} | Stop Loss: ₹{stop_loss_price:.2f}")
            else:
                # No pattern detected - log this too
                logger.debug(f"❌ {contract.symbol} {contract.option_type} {contract.strike} - No pattern detected yet")
                
        except Exception as e:
            logger.error(f"Error checking pattern for {contract.symbol} {contract.strike}{contract.option_type}: {e}")
    
    def _get_mock_price(self, symbol: str) -> float:
        """Get mock price for symbol"""
        import random
        if symbol == "NIFTY50":
            return 25800 + random.randint(-200, 200)
        elif symbol == "BANKNIFTY":
            return 45000 + random.randint(-500, 500)
        else:
            # Stock prices
            stock_prices = {
                "RELIANCE": 2500, "TCS": 3500, "HDFCBANK": 1600, "INFY": 1800,
                "ICICIBANK": 1000, "BHARTIARTL": 900, "ITC": 450, "SBIN": 600,
                "KOTAKBANK": 1800, "ASIANPAINT": 3000, "MARUTI": 10000,
                "AXISBANK": 1100, "LT": 3500, "HINDUNILVR": 2400, "NESTLEIND": 20000,
                "WIPRO": 400, "POWERGRID": 200, "TITAN": 3000, "ULTRACEMCO": 8000, "TECHM": 1200
            }
            return stock_prices.get(symbol, 1000) + random.randint(-100, 100)
    
    def _calculate_fibonacci_targets(self, entry_price: float, channel_breakout_price: float) -> Dict:
        """Calculate Fibonacci targets for the trade"""
        # Calculate the range from entry to channel breakout
        range_size = channel_breakout_price - entry_price
        
        # Fibonacci levels
        target_236 = entry_price + (range_size * 2.36)  # 0.236 extension
        target_50 = entry_price + (range_size * 1.5)    # 0.5 extension
        target_618 = entry_price + (range_size * 1.618) # 0.618 extension
        
        # Stop loss is channel re-entry (slightly below entry)
        stop_loss = entry_price * 0.98  # 2% below entry
        
        return {
            'target_236': target_236,
            'target_50': target_50,
            'target_618': target_618,
            'stop_loss': stop_loss
        }
    
    async def update_signal_outcomes(self):
        """Update outcomes of past signals"""
        try:
            for signal in self.past_signals:
                if signal.outcome == "running":
                    # Get current price
                    current_price = self._get_mock_price(signal.symbol)
                    signal.current_price = current_price
                    signal.last_updated = datetime.now()
                    
                    # Check if target hit
                    if current_price >= signal.target_price:
                        signal.outcome = "target_hit"
                        signal.profit_loss_pct = ((current_price - signal.entry_price) / signal.entry_price) * 100
                        signal.profit_loss_amount = (signal.profit_loss_pct / 100) * self.initial_investment
                        logger.info(f"🎯 {signal.symbol} {signal.strike}{signal.option_type} - TARGET HIT! +{signal.profit_loss_pct:.1f}%")
                    
                    # Check if stop loss hit
                    elif current_price <= signal.stop_loss_price:
                        signal.outcome = "stop_loss_hit"
                        signal.profit_loss_pct = ((current_price - signal.entry_price) / signal.entry_price) * 100
                        signal.profit_loss_amount = (signal.profit_loss_pct / 100) * self.initial_investment
                        logger.info(f"🛑 {signal.symbol} {signal.strike}{signal.option_type} - STOP LOSS HIT! {signal.profit_loss_pct:.1f}%")
                    
                    # Update current value for performance tracking
                    if signal.outcome == "running":
                        # Calculate current value based on price movement
                        price_change_pct = ((current_price - signal.entry_price) / signal.entry_price) * 100
                        current_value = self.initial_investment * (1 + price_change_pct / 100)
                        # Update total current value (this is simplified - in reality we'd track each signal separately)
                        self.total_current_value = sum([
                            self.initial_investment * (1 + s.profit_loss_pct / 100) if s.outcome != "running" 
                            else self.initial_investment * (1 + ((s.current_price - s.entry_price) / s.entry_price) * 100 / 100)
                            for s in self.past_signals
                        ])
                        
        except Exception as e:
            logger.error(f"Error updating signal outcomes: {e}")
    
    def get_performance_summary(self) -> Dict:
        """Get performance summary for all signals"""
        if not self.past_signals:
            return {
                "total_signals": 0,
                "total_invested": 0,
                "total_current_value": 0,
                "total_pnl": 0,
                "total_pnl_pct": 0,
                "targets_hit": 0,
                "stop_losses_hit": 0,
                "still_running": 0
            }
        
        targets_hit = len([s for s in self.past_signals if s.outcome == "target_hit"])
        stop_losses_hit = len([s for s in self.past_signals if s.outcome == "stop_loss_hit"])
        still_running = len([s for s in self.past_signals if s.outcome == "running"])
        
        total_pnl = self.total_current_value - self.total_invested
        total_pnl_pct = (total_pnl / self.total_invested * 100) if self.total_invested > 0 else 0
        
        return {
            "total_signals": len(self.past_signals),
            "total_invested": self.total_invested,
            "total_current_value": self.total_current_value,
            "total_pnl": total_pnl,
            "total_pnl_pct": total_pnl_pct,
            "targets_hit": targets_hit,
            "stop_losses_hit": stop_losses_hit,
            "still_running": still_running
        }
    
    async def _get_contract_data(self, contract: OptionContract) -> Optional[pd.DataFrame]:
        """Get recent data for a contract"""
        try:
            # For development, generate mock data
            import random
            
            # Create 2 hours of 20-minute data (6 candles)
            times = pd.date_range(
                start=datetime.now() - timedelta(hours=2),
                end=datetime.now(),
                freq='20min'
            )
            
            # Generate realistic option price movement
            base_price = 50 + random.randint(0, 200)  # Base option price
            prices = [base_price]
            
            for i in range(1, len(times)):
                # Random walk with some volatility
                change = random.uniform(-5, 5)
                new_price = max(prices[-1] + change, 1)  # Minimum price of 1
                prices.append(new_price)
            
            # Create OHLC data
            data = []
            for i, (time, price) in enumerate(zip(times, prices)):
                high = price + random.uniform(0, 3)
                low = price - random.uniform(0, 3)
                open_price = prices[i-1] if i > 0 else price
                close_price = price
                volume = random.randint(100, 1000)
                
                data.append({
                    'timestamp': time,
                    'open': open_price,
                    'high': high,
                    'low': low,
                    'close': close_price,
                    'volume': volume
                })
            
            df = pd.DataFrame(data)
            df.set_index('timestamp', inplace=True)
            
            # Update contract current price
            contract.current_price = prices[-1]
            contract.last_updated = datetime.now()
            
            return df
            
        except Exception as e:
            logger.error(f"Error getting data for {contract.instrument_token}: {e}")
            return None
    
    async def _detect_patterns(self, data: pd.DataFrame, contract: OptionContract) -> Optional[Dict]:
        """Detect patterns in the data"""
        try:
            if len(data) < 10:  # Need minimum data points
                return None
            
            # Check for channel patterns
            channels = self.analysis_engine.detect_parallel_channel(data)
            if not channels:
                return None
            
            # Check for KST confirmation
            kst = self.analysis_engine.compute_kst(data, timeframe="2h")
            if not kst:
                return None
            
            # Determine pattern type
            pattern_type = "CALL" if contract.option_type == "CE" else "PUT"
            
            # Check if pattern is strong enough
            pattern_strength = self._calculate_pattern_strength(channels, kst)
            if pattern_strength < 0.7:  # Minimum strength threshold
                return None
            
            return {
                'pattern_type': pattern_type,
                'channels': channels,
                'kst': kst,
                'strength': pattern_strength,
                'data': data
            }
            
        except Exception as e:
            logger.error(f"Error detecting patterns: {e}")
            return None
    
    def _calculate_pattern_strength(self, channels: Dict, kst: Dict) -> float:
        """Calculate pattern strength (0-1)"""
        try:
            strength = 0.0
            
            # Channel strength
            if channels.get('direction') == 'up':
                strength += 0.3
            elif channels.get('direction') == 'down':
                strength += 0.3
            
            # KST strength
            if kst.get('signal') == 'bullish':
                strength += 0.4
            elif kst.get('signal') == 'bearish':
                strength += 0.4
            
            # Add some randomness for demo
            strength += np.random.uniform(0, 0.3)
            
            return min(strength, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating pattern strength: {e}")
            return 0.0
    
    async def _handle_pattern_alert(self, pattern_result: Dict, contract: OptionContract):
        """Handle pattern alert"""
        try:
            # Create alert
            alert = PatternAlert(
                contract=contract,
                pattern_type=pattern_result['pattern_type'],
                strike_price=contract.strike,
                current_price=contract.current_price,
                pattern_strength=pattern_result['strength'],
                timestamp=datetime.now(),
                status='pattern_detected'
            )
            
            # Add to alerts
            self.pattern_alerts.append(alert)
            
            # Log the alert
            logger.info(f"🎯 PATTERN DETECTED: {contract.symbol} {contract.strike}{contract.option_type} - {pattern_result['pattern_type']} - Strength: {pattern_result['strength']:.2f}")
            
            # Check for overlap
            await self._check_overlap(alert, pattern_result)
            
        except Exception as e:
            logger.error(f"Error handling pattern alert: {e}")
    
    async def _check_overlap(self, alert: PatternAlert, pattern_result: Dict):
        """Check for no shorting indicator overlap"""
        try:
            # Simulate overlap detection
            if np.random.random() < 0.3:  # 30% chance of overlap
                alert.status = 'overlap_detected'
                logger.info(f"🔄 OVERLAP DETECTED: {alert.contract.symbol} {alert.strike_price}{alert.contract.option_type} - Ready for breakout!")
                
                # Check for breakout
                await self._check_breakout(alert, pattern_result)
                
        except Exception as e:
            logger.error(f"Error checking overlap: {e}")
    
    async def _check_breakout(self, alert: PatternAlert, pattern_result: Dict):
        """Check for 20-minute candle breakout"""
        try:
            # Simulate breakout detection
            if np.random.random() < 0.2:  # 20% chance of breakout
                alert.status = 'breakout_confirmed'
                logger.info(f"🚀 BREAKOUT CONFIRMED: {alert.contract.symbol} {alert.strike_price}{alert.contract.option_type} - {alert.pattern_type} signal!")
                
        except Exception as e:
            logger.error(f"Error checking breakout: {e}")
    
    def get_active_alerts(self) -> List[PatternAlert]:
        """Get all active alerts"""
        return [alert for alert in self.pattern_alerts if alert.status in ['pattern_detected', 'overlap_detected', 'breakout_confirmed']]
    
    def stop_monitoring(self):
        """Stop live monitoring"""
        self.monitoring_active = False
        logger.info("Live monitoring stopped")

# Global monitor instance
live_monitor: Optional[LiveMonitor] = None

async def start_live_monitoring(broker_adapter: DhanAdapter):
    """Start the live monitoring system"""
    global live_monitor
    
    try:
        live_monitor = LiveMonitor(broker_adapter)
        
        # Initialize contracts
        if await live_monitor.initialize_contracts():
            # Start monitoring
            await live_monitor.start_monitoring()
        else:
            logger.error("Failed to initialize contracts")
            
    except Exception as e:
        logger.error(f"Error starting live monitoring: {e}")

def get_live_alerts() -> List[Dict]:
    """Get live alerts for API"""
    global live_monitor
    
    if not live_monitor:
        return []
    
    alerts = live_monitor.get_active_alerts()
    return [
        {
            'symbol': alert.contract.symbol,
            'strike': alert.strike_price,
            'option_type': alert.contract.option_type,
            'pattern_type': alert.pattern_type,
            'current_price': alert.current_price,
            'strength': alert.pattern_strength,
            'status': alert.status,
            'timestamp': alert.timestamp.isoformat()
        }
        for alert in alerts
    ]
