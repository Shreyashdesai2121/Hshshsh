"""
State management for the trading system.
Handles persistence of system state and thread-safe operations.
"""
import json
import threading
from datetime import datetime
from typing import Any, Dict, Optional
from pathlib import Path
from loguru import logger
from utils import safe_json_load, safe_json_save


class StateManager:
    """Thread-safe state manager for the trading system."""
    
    def __init__(self, state_file: str = "state.json"):
        self.state_file = state_file
        self._lock = threading.Lock()
        self._state = self._load_initial_state()
    
    def _load_initial_state(self) -> Dict[str, Any]:
        """Load initial state from file or create default."""
        default_state = {
            "running": False,
            "last_run_time": None,
            "last_candle_time": None,
            "open_positions": [],
            "today_trades": [],
            "total_trades": 0,
            "total_pnl": 0.0,
            "win_rate": 0.0,
            "last_signal_time": None,
            "last_signal": None,
            "strategy_start_time": None,
            "last_state_update": None,
            "error_count": 0,
            "last_error": None
        }
        
        loaded_state = safe_json_load(self.state_file, default_state)
        
        # Merge with defaults to ensure all keys exist
        for key, value in default_state.items():
            if key not in loaded_state:
                loaded_state[key] = value
        
        return loaded_state
    
    def get_state(self) -> Dict[str, Any]:
        """Get current state (thread-safe)."""
        with self._lock:
            return self._state.copy()
    
    def update_state(self, updates: Dict[str, Any]) -> bool:
        """Update state with new values (thread-safe)."""
        with self._lock:
            self._state.update(updates)
            self._state["last_state_update"] = datetime.now().isoformat()
            return self._save_state()
    
    def _save_state(self) -> bool:
        """Save state to file."""
        return safe_json_save(self._state, self.state_file)
    
    def set_running(self, running: bool) -> bool:
        """Set running status."""
        updates = {
            "running": running,
            "strategy_start_time": datetime.now().isoformat() if running else None
        }
        return self.update_state(updates)
    
    def update_last_run(self, run_time: datetime) -> bool:
        """Update last run time."""
        return self.update_state({
            "last_run_time": run_time.isoformat()
        })
    
    def update_last_candle(self, candle_time: datetime) -> bool:
        """Update last candle time."""
        return self.update_state({
            "last_candle_time": candle_time.isoformat()
        })
    
    def add_position(self, position: Dict[str, Any]) -> bool:
        """Add new position."""
        with self._lock:
            self._state["open_positions"].append(position)
            return self._save_state()
    
    def remove_position(self, position_id: str) -> bool:
        """Remove position by ID."""
        with self._lock:
            self._state["open_positions"] = [
                pos for pos in self._state["open_positions"] 
                if pos.get("id") != position_id
            ]
            return self._save_state()
    
    def update_position(self, position_id: str, updates: Dict[str, Any]) -> bool:
        """Update existing position."""
        with self._lock:
            for i, pos in enumerate(self._state["open_positions"]):
                if pos.get("id") == position_id:
                    self._state["open_positions"][i].update(updates)
                    return self._save_state()
            return False
    
    def add_trade(self, trade: Dict[str, Any]) -> bool:
        """Add completed trade."""
        with self._lock:
            self._state["today_trades"].append(trade)
            self._state["total_trades"] += 1
            
            # Update PnL
            pnl = trade.get("pnl", 0)
            self._state["total_pnl"] += pnl
            
            # Update win rate
            if self._state["total_trades"] > 0:
                winning_trades = sum(1 for t in self._state["today_trades"] if t.get("pnl", 0) > 0)
                self._state["win_rate"] = (winning_trades / self._state["total_trades"]) * 100
            
            return self._save_state()
    
    def update_signal(self, signal: Dict[str, Any]) -> bool:
        """Update last signal information."""
        return self.update_state({
            "last_signal_time": datetime.now().isoformat(),
            "last_signal": signal
        })
    
    def log_error(self, error: str) -> bool:
        """Log error and update error count."""
        return self.update_state({
            "error_count": self._state.get("error_count", 0) + 1,
            "last_error": {
                "message": error,
                "timestamp": datetime.now().isoformat()
            }
        })
    
    def reset_daily_stats(self) -> bool:
        """Reset daily statistics."""
        return self.update_state({
            "today_trades": [],
            "last_run_time": None,
            "last_candle_time": None,
            "error_count": 0,
            "last_error": None
        })
    
    def get_open_positions(self) -> list:
        """Get list of open positions."""
        with self._lock:
            return self._state["open_positions"].copy()
    
    def get_today_trades(self) -> list:
        """Get today's trades."""
        with self._lock:
            return self._state["today_trades"].copy()
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        with self._lock:
            return {
                "total_trades": self._state["total_trades"],
                "total_pnl": self._state["total_pnl"],
                "win_rate": self._state["win_rate"],
                "open_positions": len(self._state["open_positions"]),
                "today_trades": len(self._state["today_trades"]),
                "error_count": self._state["error_count"]
            }
    
    def is_running(self) -> bool:
        """Check if strategy is running."""
        with self._lock:
            return self._state["running"]
    
    def get_last_signal(self) -> Optional[Dict[str, Any]]:
        """Get last signal information."""
        with self._lock:
            return self._state.get("last_signal")
    
    def clear_errors(self) -> bool:
        """Clear error count and last error."""
        return self.update_state({
            "error_count": 0,
            "last_error": None
        })


# Global state manager instance
state_manager = StateManager()