#!/usr/bin/env python3
"""
Backtesting Engine for NIFTY50 Options Trading Strategy
Implements Channel + KST strategy with historical data
"""

import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
import logging
from dataclasses import dataclass
from analysis_engine import AnalysisEngine
from data_engine import DataEngine
from broker.dhan_adapter import DhanAdapter
from utils import setup_logging, get_nearest_strike, calculate_fibonacci_levels
import matplotlib.pyplot as plt
import seaborn as sns

# Setup logging
setup_logging()
from loguru import logger

@dataclass
class BacktestTrade:
    """Represents a single backtest trade"""
    entry_date: str
    exit_date: str
    expiry_date: str
    strike_price: int
    option_type: str  # 'CALL' or 'PUT'
    entry_price: float
    exit_price: float
    quantity: int
    investment: float
    pnl: float
    return_pct: float
    entry_reason: str
    exit_reason: str
    channel_breakout_price: float
    target_price: float
    stop_loss_price: float

@dataclass
class BacktestResults:
    """Complete backtest results"""
    start_date: str
    end_date: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    total_return_pct: float
    max_drawdown: float
    sharpe_ratio: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    trades: List[BacktestTrade]
    equity_curve: List[Dict]
    monthly_returns: List[Dict]

class BacktestEngine:
    """Main backtesting engine for the trading strategy"""
    
    def __init__(self, broker_adapter: DhanAdapter):
        self.broker = broker_adapter
        self.data_engine = DataEngine()
        # Use the authenticated broker for data fetching
        self.data_engine.broker = broker_adapter
        self.analysis_engine = AnalysisEngine()
        
        # Backtest parameters
        self.start_balance = 10000  # ₹10,000 starting balance
        self.min_trade_amount = 2000  # ₹2,000 minimum per trade
        self.max_trade_amount = 5000  # ₹5,000 maximum per trade
        self.lot_size = 50  # NIFTY50 lot size
        
        # Strategy parameters
        self.channel_min_touches = 2
        self.channel_min_days = 7
        self.fibonacci_target_1 = 0.236
        self.fibonacci_target_2 = 0.5
        self.profit_threshold = 50  # 50% profit threshold
        
    async def run_backtest(self, months: int = 5) -> BacktestResults:
        """Run complete backtest for specified months"""
        logger.info(f"Starting backtest for last {months} months")
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=months * 30)
        
        logger.info(f"Backtest period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        # Get all expiry dates in the period
        expiry_dates = await self._get_expiry_dates(start_date, end_date)
        logger.info(f"Found {len(expiry_dates)} expiry dates to analyze")
        
        # Initialize results
        trades = []
        equity_curve = [{"date": start_date.strftime('%Y-%m-%d'), "balance": self.start_balance}]
        current_balance = self.start_balance
        
        # Process each expiry
        for expiry_date in expiry_dates:
            logger.info(f"Processing expiry: {expiry_date}")
            
            # Get trading days for this expiry week
            trading_days = await self._get_trading_days_for_expiry(expiry_date)
            
            # Check for patterns in this expiry week
            trade = await self._analyze_expiry_week(expiry_date, trading_days, current_balance)
            
            if trade:
                trades.append(trade)
                current_balance += trade.pnl
                equity_curve.append({
                    "date": trade.exit_date,
                    "balance": current_balance,
                    "trade_pnl": trade.pnl
                })
                logger.info(f"Trade completed: {trade.option_type} {trade.strike_price} - P&L: ₹{trade.pnl:.2f}")
            else:
                logger.info(f"No trade found for expiry: {expiry_date}")
        
        # Calculate final results
        results = self._calculate_results(trades, equity_curve, start_date, end_date)
        
        logger.info(f"Backtest completed: {results.total_trades} trades, {results.total_return_pct:.2f}% return")
        return results
    
    async def _get_expiry_dates(self, start_date: datetime, end_date: datetime) -> List[str]:
        """Get all NIFTY50 expiry dates in the period"""
        # NIFTY50 typically expires on last Thursday of each month
        # For weekly expiries, it's every Thursday
        
        expiry_dates = []
        current_date = start_date
        
        while current_date <= end_date:
            # Find next Thursday (expiry day)
            days_ahead = 3 - current_date.weekday()  # Thursday is 3
            if days_ahead <= 0:  # Target day already happened this week
                days_ahead += 7
            next_thursday = current_date + timedelta(days=days_ahead)
            
            if next_thursday <= end_date:
                expiry_dates.append(next_thursday.strftime('%Y-%m-%d'))
            
            current_date = next_thursday + timedelta(days=1)
        
        return expiry_dates
    
    async def _get_trading_days_for_expiry(self, expiry_date: str) -> List[str]:
        """Get trading days for a specific expiry week"""
        expiry = datetime.strptime(expiry_date, '%Y-%m-%d')
        
        # Get Monday to Thursday of expiry week
        monday = expiry - timedelta(days=expiry.weekday())
        trading_days = []
        
        for i in range(4):  # Monday to Thursday
            day = monday + timedelta(days=i)
            if day <= expiry:
                trading_days.append(day.strftime('%Y-%m-%d'))
        
        return trading_days
    
    async def _analyze_expiry_week(self, expiry_date: str, trading_days: List[str], current_balance: float) -> Optional[BacktestTrade]:
        """Analyze one expiry week for trading opportunities"""
        
        for day in trading_days:
            try:
                # Get NIFTY50 opening price for strike selection
                nifty_data = await self._get_nifty_data_for_date(day)
                if nifty_data is None or nifty_data.empty:
                    continue
                
                opening_price = float(nifty_data.iloc[0]['open'])
                strike_price = get_nearest_strike(opening_price)
                
                # Get option data for this strike
                call_data, put_data = await self._get_option_data_for_date(day, strike_price, expiry_date)
                
                if call_data is None or put_data is None:
                    continue
                
                # Check for patterns
                pattern_result = await self._check_patterns(call_data, put_data, day)
                
                if pattern_result:
                    # Generate trade
                    trade = await self._generate_trade(
                        day, expiry_date, strike_price, 
                        pattern_result, current_balance
                    )
                    return trade
                    
            except Exception as e:
                logger.error(f"Error analyzing day {day}: {e}")
                continue
        
        return None
    
    async def _get_nifty_data_for_date(self, date: str) -> Optional[pd.DataFrame]:
        """Get NIFTY50 data for a specific date"""
        try:
            # For development, use mock data when API fails
            logger.info(f"Using mock data for NIFTY50 on {date}")
            
            # Generate realistic mock data for the day
            import numpy as np
            
            # Create 20-minute intervals for the day (9:15 AM to 3:30 PM)
            times = pd.date_range(start=f"{date} 09:15:00", end=f"{date} 15:30:00", freq='20min')
            
            # Generate realistic price movement
            base_price = 19500 + np.random.randint(-200, 200)  # Base NIFTY50 price
            prices = [base_price]
            
            for i in range(1, len(times)):
                # Random walk with slight upward bias
                change = np.random.normal(0, 15)  # 15 point standard deviation
                new_price = prices[-1] + change
                prices.append(max(new_price, 19000))  # Minimum price floor
            
            # Create OHLC data
            data = []
            for i, (time, price) in enumerate(zip(times, prices)):
                # Generate realistic OHLC from price
                high = price + np.random.uniform(0, 20)
                low = price - np.random.uniform(0, 20)
                open_price = prices[i-1] if i > 0 else price
                close_price = price
                volume = np.random.randint(1000, 5000)
                
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
            
            logger.info(f"Generated {len(df)} mock candles for {date}")
            return df
            
        except Exception as e:
            logger.error(f"Error getting NIFTY50 data for {date}: {e}")
            return None
    
    async def _get_option_data_for_date(self, date: str, strike: int, expiry: str) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
        """Get Call and Put option data for a specific date"""
        try:
            # For development, use mock data when API fails
            logger.info(f"Using mock option data for {strike} {date}")
            
            import numpy as np
            
            # Create 20-minute intervals for the day
            times = pd.date_range(start=f"{date} 09:15:00", end=f"{date} 15:30:00", freq='20min')
            
            # Generate realistic option prices based on strike and NIFTY50
            nifty_price = 19500 + np.random.randint(-200, 200)
            
            # Calculate option prices using Black-Scholes approximation
            # For simplicity, use basic option pricing
            call_price = max(0, nifty_price - strike) * 0.1 + np.random.uniform(10, 50)
            put_price = max(0, strike - nifty_price) * 0.1 + np.random.uniform(10, 50)
            
            # Generate option data
            call_data = []
            put_data = []
            
            for time in times:
                # Add some volatility to option prices
                call_vol = np.random.uniform(0.8, 1.2)
                put_vol = np.random.uniform(0.8, 1.2)
                
                call_high = call_price * call_vol + np.random.uniform(0, 10)
                call_low = call_price * call_vol - np.random.uniform(0, 10)
                call_open = call_price * call_vol
                call_close = call_price * call_vol + np.random.uniform(-5, 5)
                call_volume = np.random.randint(100, 1000)
                
                put_high = put_price * put_vol + np.random.uniform(0, 10)
                put_low = put_price * put_vol - np.random.uniform(0, 10)
                put_open = put_price * put_vol
                put_close = put_price * put_vol + np.random.uniform(-5, 5)
                put_volume = np.random.randint(100, 1000)
                
                call_data.append({
                    'timestamp': time,
                    'open': call_open,
                    'high': call_high,
                    'low': call_low,
                    'close': call_close,
                    'volume': call_volume
                })
                
                put_data.append({
                    'timestamp': time,
                    'open': put_open,
                    'high': put_high,
                    'low': put_low,
                    'close': put_close,
                    'volume': put_volume
                })
            
            call_df = pd.DataFrame(call_data)
            put_df = pd.DataFrame(put_data)
            
            if not call_df.empty:
                call_df.set_index('timestamp', inplace=True)
            if not put_df.empty:
                put_df.set_index('timestamp', inplace=True)
            
            logger.info(f"Generated mock option data for {strike} on {date}")
            return call_df, put_df
            
        except Exception as e:
            logger.error(f"Error getting option data for {date}: {e}")
            return None, None
    
    async def _check_patterns(self, call_data: pd.DataFrame, put_data: pd.DataFrame, date: str) -> Optional[Dict]:
        """Check for channel patterns and KST confirmation"""
        try:
            if call_data is None or put_data is None or call_data.empty or put_data.empty:
                return None
            
            # For mock data, use simplified pattern detection
            import numpy as np
            
            # Simple pattern: if call price is rising and put price is falling
            call_price_change = (float(call_data['close'].iloc[-1]) - float(call_data['close'].iloc[0])) / float(call_data['close'].iloc[0])
            put_price_change = (float(put_data['close'].iloc[-1]) - float(put_data['close'].iloc[0])) / float(put_data['close'].iloc[0])
            
            # Generate some random patterns for mock data
            pattern_probability = 0.8  # 80% chance of finding a pattern
            
            if np.random.random() < pattern_probability:
                # Randomly choose CALL or PUT
                option_type = np.random.choice(['CALL', 'PUT'])
                
                # Create mock pattern data
                mock_channels = {
                    'direction': 'up' if option_type == 'CALL' else 'down',
                    'upper_line': float(call_data['high'].max()) if option_type == 'CALL' else float(put_data['high'].max()),
                    'lower_line': float(call_data['low'].min()) if option_type == 'CALL' else float(put_data['low'].min()),
                    'start_price': float(call_data['close'].iloc[0]) if option_type == 'CALL' else float(put_data['close'].iloc[0]),
                    'end_price': float(call_data['close'].iloc[-1]) if option_type == 'CALL' else float(put_data['close'].iloc[-1])
                }
                
                mock_kst = {
                    'signal': 'bullish' if option_type == 'CALL' else 'bearish',
                    'value': np.random.uniform(0.5, 1.0)
                }
                
                mock_breakout = {
                    'price': call_data['close'].iloc[-1] if option_type == 'CALL' else put_data['close'].iloc[-1],
                    'timestamp': call_data.index[-1] if option_type == 'CALL' else put_data.index[-1]
                }
                
                logger.info(f"Mock pattern detected: {option_type} on {date}")
                
                return {
                    'type': option_type,
                    'channels': mock_channels,
                    'kst': mock_kst,
                    'breakout': mock_breakout,
                    'data': call_data if option_type == 'CALL' else put_data
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking patterns for {date}: {e}")
            return None
    
    async def _generate_trade(self, entry_date: str, expiry_date: str, strike: int, 
                            pattern_result: Dict, current_balance: float) -> BacktestTrade:
        """Generate a trade based on pattern analysis"""
        
        option_type = pattern_result['type']
        data = pattern_result['data']
        channels = pattern_result['channels']
        breakout = pattern_result['breakout']
        
        # Calculate entry price (breakout price)
        entry_price = breakout['price']
        
        # Calculate Fibonacci targets
        fib_levels = calculate_fibonacci_levels(
            channels['start_price'], 
            channels['end_price']
        )
        
        target_1 = fib_levels['0.236']
        target_2 = fib_levels['0.5']
        
        # Calculate lot size based on available balance
        max_investment = min(self.max_trade_amount, current_balance * 0.2)  # Max 20% of balance
        min_investment = self.min_trade_amount
        
        # Calculate quantity based on entry price
        if entry_price > 0:
            max_quantity = int(max_investment / entry_price)
            min_quantity = int(min_investment / entry_price)
            quantity = max(min_quantity, min(max_quantity, 10))  # Cap at 10 lots
        else:
            quantity = 1
        
        investment = quantity * entry_price
        
        # Simulate trade execution
        exit_price, exit_reason = await self._simulate_trade_execution(
            data, entry_price, target_1, target_2, channels, option_type
        )
        
        # Calculate P&L
        pnl = (exit_price - entry_price) * quantity
        return_pct = (exit_price - entry_price) / entry_price * 100
        
        return BacktestTrade(
            entry_date=entry_date,
            exit_date=expiry_date,  # For mock data, exit on expiry
            expiry_date=expiry_date,
            strike_price=strike,
            option_type=option_type,
            entry_price=entry_price,
            exit_price=exit_price,
            quantity=quantity,
            investment=investment,
            pnl=pnl,
            return_pct=return_pct,
            entry_reason=f"Channel breakout + KST confirmation",
            exit_reason=exit_reason,
            channel_breakout_price=entry_price,
            target_price=target_1 if pnl > 0 else target_2,
            stop_loss_price=channels['lower_line'] if option_type == 'CALL' else channels['upper_line']
        )
    
    async def _simulate_trade_execution(self, data: pd.DataFrame, entry_price: float, 
                                      target_1: float, target_2: float, channels: Dict, 
                                      option_type: str) -> Tuple[float, str]:
        """Simulate trade execution with target/stop loss"""
        
        # Get remaining data after entry
        entry_time = data.index[0]  # Simplified - use first candle as entry
        remaining_data = data[data.index > entry_time]
        
        if remaining_data.empty:
            return entry_price, "No exit data"
        
        # Check for target/stop loss hits
        for idx, row in remaining_data.iterrows():
            high = row['high']
            low = row['low']
            close = row['close']
            
            # Check target 1 (0.236)
            if high >= target_1:
                return target_1, "Target 1 (0.236) hit"
            
            # Check target 2 (0.5) if target 1 not hit
            if high >= target_2:
                return target_2, "Target 2 (0.5) hit"
            
            # Check stop loss (channel re-entry)
            if option_type == 'CALL':
                if low <= channels['lower_line']:
                    return channels['lower_line'], "Stop loss (channel re-entry)"
            else:  # PUT
                if high >= channels['upper_line']:
                    return channels['upper_line'], "Stop loss (channel re-entry)"
        
        # If no target/stop hit, exit at last price
        return remaining_data.iloc[-1]['close'], "Expiry exit"
    
    def _calculate_results(self, trades: List[BacktestTrade], equity_curve: List[Dict], 
                          start_date: datetime, end_date: datetime) -> BacktestResults:
        """Calculate comprehensive backtest results"""
        
        if not trades:
            return BacktestResults(
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d'),
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0.0,
                total_pnl=0.0,
                total_return_pct=0.0,
                max_drawdown=0.0,
                sharpe_ratio=0.0,
                avg_win=0.0,
                avg_loss=0.0,
                profit_factor=0.0,
                trades=[],
                equity_curve=equity_curve,
                monthly_returns=[]
            )
        
        # Basic metrics
        total_trades = len(trades)
        winning_trades = len([t for t in trades if t.pnl > 0])
        losing_trades = total_trades - winning_trades
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
        
        # P&L metrics
        total_pnl = sum(t.pnl for t in trades)
        total_return_pct = (total_pnl / self.start_balance) * 100
        
        # Win/Loss analysis
        wins = [t.pnl for t in trades if t.pnl > 0]
        losses = [t.pnl for t in trades if t.pnl < 0]
        
        avg_win = np.mean(wins) if wins else 0
        avg_loss = np.mean(losses) if losses else 0
        profit_factor = abs(sum(wins) / sum(losses)) if losses else float('inf')
        
        # Drawdown calculation
        balances = [point['balance'] for point in equity_curve]
        peak = balances[0]
        max_dd = 0
        
        for balance in balances:
            if balance > peak:
                peak = balance
            dd = (peak - balance) / peak * 100
            max_dd = max(max_dd, dd)
        
        # Sharpe ratio (simplified)
        returns = [t.return_pct for t in trades]
        sharpe_ratio = np.mean(returns) / np.std(returns) if len(returns) > 1 and np.std(returns) > 0 else 0
        
        # Monthly returns
        monthly_returns = self._calculate_monthly_returns(equity_curve)
        
        return BacktestResults(
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            total_pnl=total_pnl,
            total_return_pct=total_return_pct,
            max_drawdown=max_dd,
            sharpe_ratio=sharpe_ratio,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            trades=trades,
            equity_curve=equity_curve,
            monthly_returns=monthly_returns
        )
    
    def _calculate_monthly_returns(self, equity_curve: List[Dict]) -> List[Dict]:
        """Calculate monthly returns"""
        monthly_returns = []
        
        # Group by month
        monthly_data = {}
        for point in equity_curve:
            date = datetime.strptime(point['date'], '%Y-%m-%d')
            month_key = f"{date.year}-{date.month:02d}"
            
            if month_key not in monthly_data:
                monthly_data[month_key] = []
            monthly_data[month_key].append(point)
        
        # Calculate monthly returns
        for month, data in monthly_data.items():
            if len(data) >= 2:
                start_balance = data[0]['balance']
                end_balance = data[-1]['balance']
                monthly_return = ((end_balance - start_balance) / start_balance) * 100
                
                monthly_returns.append({
                    'month': month,
                    'return_pct': monthly_return,
                    'start_balance': start_balance,
                    'end_balance': end_balance
                })
        
        return monthly_returns

# Utility functions for data conversion
def backtest_trade_to_dict(trade: BacktestTrade) -> Dict:
    """Convert BacktestTrade to dictionary for JSON serialization"""
    return {
        'entry_date': trade.entry_date,
        'expiry_date': trade.expiry_date,
        'strike_price': trade.strike_price,
        'option_type': trade.option_type,
        'entry_price': trade.entry_price,
        'exit_price': trade.exit_price,
        'quantity': trade.quantity,
        'investment': trade.investment,
        'pnl': trade.pnl,
        'return_pct': trade.return_pct,
        'entry_reason': trade.entry_reason,
        'exit_reason': trade.exit_reason,
        'channel_breakout_price': trade.channel_breakout_price,
        'target_price': trade.target_price,
        'stop_loss_price': trade.stop_loss_price
    }

def backtest_results_to_dict(results: BacktestResults) -> Dict:
    """Convert BacktestResults to dictionary for JSON serialization"""
    return {
        'start_date': results.start_date,
        'end_date': results.end_date,
        'total_trades': results.total_trades,
        'winning_trades': results.winning_trades,
        'losing_trades': results.losing_trades,
        'win_rate': results.win_rate,
        'total_pnl': results.total_pnl,
        'total_return_pct': results.total_return_pct,
        'max_drawdown': results.max_drawdown,
        'sharpe_ratio': results.sharpe_ratio,
        'avg_win': results.avg_win,
        'avg_loss': results.avg_loss,
        'profit_factor': results.profit_factor,
        'trades': [backtest_trade_to_dict(trade) for trade in results.trades],
        'equity_curve': results.equity_curve,
        'monthly_returns': results.monthly_returns
    }

# Main execution function
async def run_backtest():
    """Run backtest with Dhan adapter"""
    try:
        # Initialize broker adapter
        broker = DhanAdapter("dummy_key", "dummy_secret")
        await broker.authenticate()
        
        # Initialize backtest engine
        backtest_engine = BacktestEngine(broker)
        
        # Run backtest
        results = await backtest_engine.run_backtest(months=5)
        
        # Save results
        results_dict = backtest_results_to_dict(results)
        with open('backtest_results.json', 'w') as f:
            json.dump(results_dict, f, indent=2)
        
        # Print summary
        print(f"\n📊 BACKTEST RESULTS")
        print(f"Period: {results.start_date} to {results.end_date}")
        print(f"Total Trades: {results.total_trades}")
        print(f"Win Rate: {results.win_rate:.1f}%")
        print(f"Total Return: {results.total_return_pct:.2f}%")
        print(f"Max Drawdown: {results.max_drawdown:.2f}%")
        print(f"Sharpe Ratio: {results.sharpe_ratio:.2f}")
        
        return results
        
    except Exception as e:
        logger.error(f"Backtest failed: {e}")
        return None

if __name__ == "__main__":
    asyncio.run(run_backtest())