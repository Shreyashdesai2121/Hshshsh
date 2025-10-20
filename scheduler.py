"""
Scheduler for orchestrating the trading strategy execution.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Optional
from loguru import logger

from config import settings
from data_engine import data_engine
from analysis_engine import analysis_engine
from execution_engine import execution_engine
from state_manager import state_manager
from utils import get_next_candle_time, is_trading_hours


class TradingScheduler:
    """Scheduler for orchestrating the trading strategy execution."""
    
    def __init__(self):
        self.is_running = False
        self.scheduler_task: Optional[asyncio.Task] = None
        self.last_run_time: Optional[datetime] = None
        self.next_run_time: Optional[datetime] = None
        self.strategy_start_time: Optional[datetime] = None
    
    async def start(self):
        """Start the trading scheduler."""
        try:
            if self.is_running:
                logger.warning("Scheduler is already running")
                return
            
            # Authenticate with broker
            if not await data_engine.authenticate():
                logger.error("Failed to authenticate with broker")
                return
            
            # Start execution engine
            await execution_engine.start()
            
            # Start scheduler
            self.is_running = True
            self.strategy_start_time = datetime.now()
            self.scheduler_task = asyncio.create_task(self._run_scheduler())
            
            # Update state
            state_manager.set_running(True)
            state_manager.update_state({
                "strategy_start_time": self.strategy_start_time.isoformat()
            })
            
            logger.info("Trading scheduler started")
        
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
            state_manager.log_error(f"Failed to start scheduler: {e}")
            raise
    
    async def stop(self):
        """Stop the trading scheduler."""
        try:
            if not self.is_running:
                logger.warning("Scheduler is not running")
                return
            
            # Stop scheduler
            self.is_running = False
            if self.scheduler_task:
                self.scheduler_task.cancel()
                try:
                    await self.scheduler_task
                except asyncio.CancelledError:
                    pass
            
            # Stop execution engine
            await execution_engine.stop()
            
            # Update state
            state_manager.set_running(False)
            
            logger.info("Trading scheduler stopped")
        
        except Exception as e:
            logger.error(f"Failed to stop scheduler: {e}")
            state_manager.log_error(f"Failed to stop scheduler: {e}")
    
    async def _run_scheduler(self):
        """Main scheduler loop."""
        while self.is_running:
            try:
                # Check if strategy should run
                if not settings.run_strategy:
                    await asyncio.sleep(60)  # Check every minute
                    continue
                
                # Check trading hours
                if not self._is_trading_hours():
                    await asyncio.sleep(60)  # Check every minute
                    continue
                
                # Check if it's time to run
                if not self._should_run_now():
                    await asyncio.sleep(30)  # Check every 30 seconds
                    continue
                
                # Run strategy
                await self._run_strategy()
                
                # Update last run time
                self.last_run_time = datetime.now()
                state_manager.update_last_run(self.last_run_time)
                
                # Calculate next run time
                self.next_run_time = get_next_candle_time(
                    self.last_run_time, 
                    settings.scheduler_candle_minutes
                )
                
                # Wait until next run time
                wait_seconds = (self.next_run_time - datetime.now()).total_seconds()
                if wait_seconds > 0:
                    await asyncio.sleep(wait_seconds)
            
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                state_manager.log_error(f"Scheduler error: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def _run_strategy(self):
        """Run the trading strategy."""
        try:
            logger.info("Running trading strategy...")
            
            # Get NIFTY50 spot price
            spot_price = await data_engine.get_nifty_spot()
            if spot_price <= 0:
                logger.error("Could not get NIFTY50 spot price")
                return
            
            # Get nearest strike
            strike = data_engine.get_nearest_strike(spot_price)
            logger.info(f"NIFTY50 spot: {spot_price}, Nearest strike: {strike}")
            
            # Get call/put data
            data = await data_engine.get_call_put_data(strike, lookback_days=30)
            if not data:
                logger.error("Could not get call/put data")
                return
            
            # Validate data quality
            for option_type in ["CE", "PE"]:
                for timeframe in ["20min", "2h"]:
                    if option_type in data and timeframe in data[option_type]:
                        df = data[option_type][timeframe]
                        if not data_engine.validate_data_quality(df):
                            logger.warning(f"Poor data quality for {option_type} {timeframe}")
                            return
            
            # Generate trading signal
            signal = analysis_engine.generate_trade_signal(
                data["CE"]["20min"],
                data["CE"]["2h"],
                data["PE"]["20min"],
                data["PE"]["2h"]
            )
            
            if signal:
                logger.info(f"Generated signal: {signal.signal_type.value} {signal.instrument}")
                
                # Update signal in state
                state_manager.update_signal(signal_to_dict(signal))
                
                # Execute signal
                success = await execution_engine.execute_signal(signal)
                if success:
                    logger.info("Signal executed successfully")
                else:
                    logger.warning("Failed to execute signal")
            else:
                logger.debug("No signal generated")
            
            # Update last candle time
            state_manager.update_last_candle(datetime.now())
            
        except Exception as e:
            logger.error(f"Error running strategy: {e}")
            state_manager.log_error(f"Strategy error: {e}")
    
    def _is_trading_hours(self) -> bool:
        """Check if current time is within trading hours."""
        return is_trading_hours(
            datetime.now(),
            settings.trading_start.strftime("%H:%M"),
            settings.trading_end.strftime("%H:%M")
        )
    
    def _should_run_now(self) -> bool:
        """Check if strategy should run now."""
        now = datetime.now()
        
        # If this is the first run, run immediately
        if self.last_run_time is None:
            return True
        
        # Check if enough time has passed since last run
        time_since_last_run = (now - self.last_run_time).total_seconds()
        min_interval = settings.scheduler_candle_minutes * 60  # Convert to seconds
        
        return time_since_last_run >= min_interval
    
    def get_status(self) -> dict:
        """Get scheduler status."""
        return {
            "is_running": self.is_running,
            "last_run_time": self.last_run_time.isoformat() if self.last_run_time else None,
            "next_run_time": self.next_run_time.isoformat() if self.next_run_time else None,
            "strategy_start_time": self.strategy_start_time.isoformat() if self.strategy_start_time else None,
            "trading_hours": self._is_trading_hours(),
            "should_run": self._should_run_now() if self.is_running else False
        }
    
    def get_next_run_time(self) -> Optional[datetime]:
        """Get next scheduled run time."""
        return self.next_run_time
    
    def get_last_run_time(self) -> Optional[datetime]:
        """Get last run time."""
        return self.last_run_time


# Global scheduler instance
trading_scheduler = TradingScheduler()