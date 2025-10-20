"""
Execution engine for order management and position tracking.
"""
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from loguru import logger

from config import settings
from models import TradeSignal, Position, Trade, PositionSide, OrderType, OrderStatus
from data_engine import data_engine
from analysis_engine import analysis_engine
from state_manager import state_manager
from utils import safe_json_save, ensure_directory


class ExecutionEngine:
    """Execution engine for order management and position tracking."""
    
    def __init__(self):
        self.active_positions: Dict[str, Position] = {}
        self.pending_orders: Dict[str, Dict[str, Any]] = {}
        self.trades_history: List[Trade] = []
        self.is_running = False
        self.monitor_task = None
    
    async def start(self):
        """Start the execution engine."""
        try:
            self.is_running = True
            self.monitor_task = asyncio.create_task(self._monitor_positions())
            logger.info("Execution engine started")
        except Exception as e:
            logger.error(f"Failed to start execution engine: {e}")
            raise
    
    async def stop(self):
        """Stop the execution engine."""
        try:
            self.is_running = False
            if self.monitor_task:
                self.monitor_task.cancel()
                try:
                    await self.monitor_task
                except asyncio.CancelledError:
                    pass
            logger.info("Execution engine stopped")
        except Exception as e:
            logger.error(f"Failed to stop execution engine: {e}")
    
    async def execute_signal(self, signal: TradeSignal) -> bool:
        """Execute a trading signal."""
        try:
            if not signal:
                return False
            
            # Check if we can trade (one trade per day limit)
            if settings.one_trade_per_day and self._has_traded_today():
                logger.info("One trade per day limit reached")
                return False
            
            # Check trading hours
            if not self._is_trading_hours():
                logger.info("Outside trading hours")
                return False
            
            # Check margin availability
            if not await self._check_margin(signal):
                logger.warning("Insufficient margin for trade")
                return False
            
            # Get instrument token
            instrument_token = await self._get_instrument_token(signal)
            if not instrument_token:
                logger.error("Failed to get instrument token")
                return False
            
            # Place order
            order_result = await self._place_order(signal, instrument_token)
            if not order_result["success"]:
                logger.error(f"Failed to place order: {order_result['error']}")
                return False
            
            # Create position
            position = self._create_position(signal, order_result)
            self.active_positions[position.id] = position
            
            # Update state
            state_manager.add_position(position_to_dict(position))
            
            logger.info(f"Successfully executed signal: {signal.signal_type.value} {signal.instrument}")
            return True
        
        except Exception as e:
            logger.error(f"Error executing signal: {e}")
            return False
    
    async def _monitor_positions(self):
        """Monitor active positions for exit conditions."""
        while self.is_running:
            try:
                for position_id, position in list(self.active_positions.items()):
                    await self._check_position_exit(position)
                
                # Update state
                state_manager.update_state({
                    "open_positions": [position_to_dict(pos) for pos in self.active_positions.values()]
                })
                
                await asyncio.sleep(60)  # Check every minute
            
            except Exception as e:
                logger.error(f"Error in position monitoring: {e}")
                await asyncio.sleep(60)
    
    async def _check_position_exit(self, position: Position):
        """Check if position should be exited."""
        try:
            # Get current price
            current_price = await data_engine.get_live_price(position.instrument)
            if current_price <= 0:
                logger.warning(f"Could not get current price for {position.instrument}")
                return
            
            # Update position with current price
            position.current_price = current_price
            position.unrealized_pnl = analysis_engine.calculate_position_pnl(
                position.entry_price, current_price, position.quantity, position.side.value
            )
            
            # Check exit conditions
            should_exit, reason = analysis_engine.should_exit_position(
                position_to_dict(position), current_price, position.channel_data
            )
            
            if should_exit:
                await self._exit_position(position, reason, current_price)
        
        except Exception as e:
            logger.error(f"Error checking position exit: {e}")
    
    async def _exit_position(self, position: Position, reason: str, exit_price: float):
        """Exit a position."""
        try:
            # Place exit order
            order_result = await self._place_exit_order(position, exit_price)
            if not order_result["success"]:
                logger.error(f"Failed to exit position: {order_result['error']}")
                return
            
            # Create trade record
            trade = self._create_trade(position, exit_price, reason)
            self.trades_history.append(trade)
            
            # Remove from active positions
            del self.active_positions[position.id]
            state_manager.remove_position(position.id)
            
            # Add to trade history
            state_manager.add_trade(trade_to_dict(trade))
            
            logger.info(f"Exited position {position.id}: {reason} at {exit_price}")
        
        except Exception as e:
            logger.error(f"Error exiting position: {e}")
    
    async def _place_order(self, signal: TradeSignal, instrument_token: str) -> Dict[str, Any]:
        """Place an order for a signal."""
        try:
            if settings.mode == "dry_run":
                # Simulate order placement
                order_id = str(uuid.uuid4())
                filled_price = signal.entry_price * (1 + settings.slippage)
                
                logger.info(f"DRY RUN: Placed order {order_id} for {signal.instrument} at {filled_price}")
                
                return {
                    "success": True,
                    "order_id": order_id,
                    "filled_price": filled_price
                }
            else:
                # Place actual order
                order_type = "MARKET" if signal.signal_type in [SignalType.BUY_CALL, SignalType.BUY_PUT] else "LIMIT"
                
                response = await data_engine.broker.place_order(
                    instrument_token=instrument_token,
                    qty=signal.quantity,
                    order_type=order_type,
                    price=signal.entry_price if order_type == "LIMIT" else None
                )
                
                if response.success:
                    return {
                        "success": True,
                        "order_id": response.order_id,
                        "filled_price": response.filled_price or signal.entry_price
                    }
                else:
                    return {
                        "success": False,
                        "error": response.error
                    }
        
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return {"success": False, "error": str(e)}
    
    async def _place_exit_order(self, position: Position, exit_price: float) -> Dict[str, Any]:
        """Place an exit order for a position."""
        try:
            if settings.mode == "dry_run":
                # Simulate order placement
                order_id = str(uuid.uuid4())
                filled_price = exit_price * (1 - settings.slippage)
                
                logger.info(f"DRY RUN: Exited position {position.id} at {filled_price}")
                
                return {
                    "success": True,
                    "order_id": order_id,
                    "filled_price": filled_price
                }
            else:
                # Place actual exit order
                response = await data_engine.broker.place_order(
                    instrument_token=position.instrument,
                    qty=position.quantity,
                    order_type="MARKET",
                    price=None
                )
                
                if response.success:
                    return {
                        "success": True,
                        "order_id": response.order_id,
                        "filled_price": response.filled_price or exit_price
                    }
                else:
                    return {
                        "success": False,
                        "error": response.error
                    }
        
        except Exception as e:
            logger.error(f"Error placing exit order: {e}")
            return {"success": False, "error": str(e)}
    
    def _create_position(self, signal: TradeSignal, order_result: Dict[str, Any]) -> Position:
        """Create a position from a signal and order result."""
        position_id = str(uuid.uuid4())
        
        return Position(
            id=position_id,
            instrument=signal.instrument,
            strike=signal.strike,
            option_type=signal.option_type,
            side=PositionSide.LONG if signal.signal_type in [SignalType.BUY_CALL, SignalType.BUY_PUT] else PositionSide.SHORT,
            quantity=signal.quantity,
            entry_price=order_result["filled_price"],
            entry_time=datetime.now(),
            target_price=signal.target_price,
            stop_loss_price=signal.stop_loss_price,
            current_price=order_result["filled_price"],
            unrealized_pnl=0.0,
            channel_data=signal.channel_data,
            kst_data=signal.kst_data
        )
    
    def _create_trade(self, position: Position, exit_price: float, reason: str) -> Trade:
        """Create a trade record from a position."""
        trade_id = str(uuid.uuid4())
        pnl = analysis_engine.calculate_position_pnl(
            position.entry_price, exit_price, position.quantity, position.side.value
        )
        
        return Trade(
            id=trade_id,
            instrument=position.instrument,
            strike=position.strike,
            option_type=position.option_type,
            side=position.side,
            quantity=position.quantity,
            entry_price=position.entry_price,
            exit_price=exit_price,
            entry_time=position.entry_time,
            exit_time=datetime.now(),
            pnl=pnl,
            fees=0.0,  # TODO: Calculate actual fees
            reason=reason,
            channel_data=position.channel_data.__dict__ if position.channel_data else None,
            kst_data=position.kst_data.__dict__ if position.kst_data else None
        )
    
    async def _get_instrument_token(self, signal: TradeSignal) -> Optional[str]:
        """Get instrument token for a signal."""
        try:
            # TODO: Implement proper expiry calculation
            expiry = "2024-01-25"  # Placeholder
            
            return await data_engine.get_option_instrument_token(
                signal.strike, signal.option_type, expiry
            )
        except Exception as e:
            logger.error(f"Error getting instrument token: {e}")
            return None
    
    async def _check_margin(self, signal: TradeSignal) -> bool:
        """Check if sufficient margin is available."""
        try:
            if settings.mode == "dry_run":
                return True
            
            response = await data_engine.broker.get_margin()
            if response.success:
                # TODO: Implement proper margin calculation
                required_margin = signal.entry_price * signal.quantity
                available_margin = response.data.get("available_margin", 0)
                return available_margin >= required_margin
            else:
                logger.warning(f"Could not check margin: {response.error}")
                return False
        except Exception as e:
            logger.error(f"Error checking margin: {e}")
            return False
    
    def _has_traded_today(self) -> bool:
        """Check if we've already traded today."""
        today_trades = state_manager.get_today_trades()
        return len(today_trades) > 0
    
    def _is_trading_hours(self) -> bool:
        """Check if current time is within trading hours."""
        from utils import is_trading_hours
        return is_trading_hours(
            datetime.now(), 
            settings.trading_start.strftime("%H:%M"), 
            settings.trading_end.strftime("%H:%M")
        )
    
    async def force_close_all(self) -> bool:
        """Force close all open positions."""
        try:
            for position in list(self.active_positions.values()):
                await self._exit_position(position, "force_close", position.current_price)
            
            logger.info("Force closed all positions")
            return True
        except Exception as e:
            logger.error(f"Error force closing positions: {e}")
            return False
    
    def get_active_positions(self) -> List[Position]:
        """Get list of active positions."""
        return list(self.active_positions.values())
    
    def get_trades_history(self) -> List[Trade]:
        """Get trade history."""
        return self.trades_history.copy()
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics."""
        try:
            total_trades = len(self.trades_history)
            if total_trades == 0:
                return {
                    "total_trades": 0,
                    "winning_trades": 0,
                    "losing_trades": 0,
                    "win_rate": 0.0,
                    "total_pnl": 0.0,
                    "avg_trade_pnl": 0.0,
                    "best_trade": 0.0,
                    "worst_trade": 0.0
                }
            
            winning_trades = [t for t in self.trades_history if t.pnl > 0]
            losing_trades = [t for t in self.trades_history if t.pnl < 0]
            
            total_pnl = sum(t.pnl for t in self.trades_history)
            win_rate = (len(winning_trades) / total_trades) * 100
            avg_trade_pnl = total_pnl / total_trades
            
            best_trade = max(t.pnl for t in self.trades_history) if self.trades_history else 0
            worst_trade = min(t.pnl for t in self.trades_history) if self.trades_history else 0
            
            return {
                "total_trades": total_trades,
                "winning_trades": len(winning_trades),
                "losing_trades": len(losing_trades),
                "win_rate": win_rate,
                "total_pnl": total_pnl,
                "avg_trade_pnl": avg_trade_pnl,
                "best_trade": best_trade,
                "worst_trade": worst_trade
            }
        
        except Exception as e:
            logger.error(f"Error calculating performance metrics: {e}")
            return {}


# Global execution engine instance
execution_engine = ExecutionEngine()