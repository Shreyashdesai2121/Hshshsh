"""
FastAPI backend application for the trading system.
"""
import asyncio
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from loguru import logger

from config import settings
from scheduler import trading_scheduler
from execution_engine import execution_engine
from state_manager import state_manager
from data_engine import data_engine
from analysis_engine import analysis_engine
from models import signal_to_dict, position_to_dict, trade_to_dict
from backtest_engine import BacktestEngine, backtest_results_to_dict
from live_monitor import start_live_monitoring, get_live_alerts
from utils import setup_logging


# Setup logging
setup_logging(settings.log_level, settings.logs_dir)

# Create FastAPI app
app = FastAPI(
    title="NIFTY50 Trading System",
    description="Algorithmic trading system for NIFTY50 options using channel breakout and KST strategy",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
    
    async def broadcast(self, message: str):
        for connection in self.active_connections.copy():
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")
                self.disconnect(connection)

manager = ConnectionManager()

# Pydantic models for API
class StrategyStartRequest(BaseModel):
    mode: Optional[str] = None
    quantity: Optional[int] = None
    one_trade_per_day: Optional[bool] = None

class StrategyStopRequest(BaseModel):
    force_close: Optional[bool] = False

class ConfigUpdateRequest(BaseModel):
    quantity: Optional[int] = None
    one_trade_per_day: Optional[bool] = None
    slippage: Optional[float] = None

# API Endpoints
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "NIFTY50 Trading System API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "scheduler_running": trading_scheduler.is_running,
        "execution_engine_running": execution_engine.is_running
    }

@app.post("/start_strategy")
async def start_strategy(request: StrategyStartRequest = None):
    """Start the trading strategy."""
    try:
        if trading_scheduler.is_running:
            return JSONResponse(
                status_code=400,
                content={"error": "Strategy is already running"}
            )
        
        # Update config if provided
        if request:
            if request.mode:
                settings.mode = request.mode
            if request.quantity:
                settings.quantity = request.quantity
            if request.one_trade_per_day is not None:
                settings.one_trade_per_day = request.one_trade_per_day
        
        # Start scheduler
        await trading_scheduler.start()
        
        # Broadcast update
        await manager.broadcast(json.dumps({
            "type": "strategy_started",
            "timestamp": datetime.now().isoformat()
        }))
        
        return {
            "success": True,
            "message": "Strategy started successfully",
            "mode": settings.mode,
            "quantity": settings.quantity,
            "one_trade_per_day": settings.one_trade_per_day
        }
    
    except Exception as e:
        logger.error(f"Error starting strategy: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to start strategy: {str(e)}"}
        )

@app.post("/stop_strategy")
async def stop_strategy(request: StrategyStopRequest = None):
    """Stop the trading strategy."""
    try:
        if not trading_scheduler.is_running:
            return JSONResponse(
                status_code=400,
                content={"error": "Strategy is not running"}
            )
        
        # Force close positions if requested
        if request and request.force_close:
            await execution_engine.force_close_all()
        
        # Stop scheduler
        await trading_scheduler.stop()
        
        # Broadcast update
        await manager.broadcast(json.dumps({
            "type": "strategy_stopped",
            "timestamp": datetime.now().isoformat()
        }))
        
        return {
            "success": True,
            "message": "Strategy stopped successfully"
        }
    
    except Exception as e:
        logger.error(f"Error stopping strategy: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to stop strategy: {str(e)}"}
        )

@app.get("/status")
async def get_status():
    """Get system status."""
    try:
        state = state_manager.get_state()
        scheduler_status = trading_scheduler.get_status()
        
        return {
            "running": state["running"],
            "last_run_time": state["last_run_time"],
            "last_candle_time": state["last_candle_time"],
            "open_positions": len(state["open_positions"]),
            "today_trades": len(state["today_trades"]),
            "total_trades": state["total_trades"],
            "total_pnl": state["total_pnl"],
            "win_rate": state["win_rate"],
            "error_count": state["error_count"],
            "last_error": state["last_error"],
            "strategy_start_time": state["strategy_start_time"],
            "scheduler_status": scheduler_status
        }
    
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to get status: {str(e)}"}
        )

@app.get("/signals")
async def get_signals(limit: int = 10):
    """Get recent signals."""
    try:
        state = state_manager.get_state()
        last_signal = state.get("last_signal")
        
        signals = []
        if last_signal:
            signals.append(last_signal)
        
        return {
            "signals": signals,
            "count": len(signals)
        }
    
    except Exception as e:
        logger.error(f"Error getting signals: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to get signals: {str(e)}"}
        )

@app.get("/performance")
async def get_performance():
    """Get performance metrics."""
    try:
        metrics = execution_engine.get_performance_metrics()
        state = state_manager.get_state()
        
        return {
            **metrics,
            "open_positions": len(state["open_positions"]),
            "today_trades": len(state["today_trades"]),
            "error_count": state["error_count"]
        }
    
    except Exception as e:
        logger.error(f"Error getting performance: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to get performance: {str(e)}"}
        )

@app.get("/positions")
async def get_positions():
    """Get open positions."""
    try:
        positions = execution_engine.get_active_positions()
        return {
            "positions": [position_to_dict(pos) for pos in positions],
            "count": len(positions)
        }
    
    except Exception as e:
        logger.error(f"Error getting positions: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to get positions: {str(e)}"}
        )

@app.get("/trades")
async def get_trades(limit: int = 50):
    """Get trade history."""
    try:
        trades = execution_engine.get_trades_history()
        if limit > 0:
            trades = trades[-limit:]
        
        return {
            "trades": [trade_to_dict(trade) for trade in trades],
            "count": len(trades)
        }
    
    except Exception as e:
        logger.error(f"Error getting trades: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to get trades: {str(e)}"}
        )

@app.post("/force_close_all")
async def force_close_all():
    """Force close all open positions."""
    try:
        success = await execution_engine.force_close_all()
        
        if success:
            # Broadcast update
            await manager.broadcast(json.dumps({
                "type": "positions_force_closed",
                "timestamp": datetime.now().isoformat()
            }))
            
            return {"success": True, "message": "All positions force closed"}
        else:
            return JSONResponse(
                status_code=500,
                content={"error": "Failed to force close positions"}
            )
    
    except Exception as e:
        logger.error(f"Error force closing positions: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to force close positions: {str(e)}"}
        )

@app.get("/logs")
async def get_logs(lines: int = 100):
    """Get recent log entries."""
    try:
        log_file = f"{settings.logs_dir}/strategy.log"
        try:
            with open(log_file, 'r') as f:
                log_lines = f.readlines()
                recent_lines = log_lines[-lines:] if len(log_lines) > lines else log_lines
                return {
                    "logs": [line.strip() for line in recent_lines],
                    "count": len(recent_lines)
                }
        except FileNotFoundError:
            return {"logs": [], "count": 0}
    
    except Exception as e:
        logger.error(f"Error getting logs: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to get logs: {str(e)}"}
        )

@app.get("/state")
async def get_state():
    """Get current system state."""
    try:
        return state_manager.get_state()
    
    except Exception as e:
        logger.error(f"Error getting state: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to get state: {str(e)}"}
        )

@app.put("/config")
async def update_config(request: ConfigUpdateRequest):
    """Update configuration."""
    try:
        if request.quantity is not None:
            settings.quantity = request.quantity
        if request.one_trade_per_day is not None:
            settings.one_trade_per_day = request.one_trade_per_day
        if request.slippage is not None:
            settings.slippage = request.slippage
        
        return {
            "success": True,
            "message": "Configuration updated",
            "config": {
                "quantity": settings.quantity,
                "one_trade_per_day": settings.one_trade_per_day,
                "slippage": settings.slippage
            }
        }
    
    except Exception as e:
        logger.error(f"Error updating config: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to update config: {str(e)}"}
        )

@app.get("/market_data")
async def get_market_data():
    """Get current market data."""
    try:
        spot_price = await data_engine.get_nifty_spot()
        strike = data_engine.get_nearest_strike(spot_price)
        
        return {
            "nifty_spot": spot_price,
            "nearest_strike": strike,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error getting market data: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to get market data: {str(e)}"}
        )

# Backtesting endpoints
@app.post("/backtest/run")
async def run_backtest(months: int = 5):
    """Run backtesting for specified number of months."""
    try:
        logger.info(f"Starting backtest for {months} months")
        
        # Initialize backtest engine with proper broker
        from broker.dhan_adapter import DhanAdapter
        broker_adapter = DhanAdapter(settings.dhan_api_key, settings.dhan_api_secret)
        
        # Authenticate the broker before running backtest
        auth_result = await broker_adapter.authenticate()
        if not auth_result.success:
            logger.error(f"Broker authentication failed: {auth_result.error}")
            return {"error": f"Broker authentication failed: {auth_result.error}"}
        
        backtest_engine = BacktestEngine(broker_adapter)
        
        # Run backtest
        results = await backtest_engine.run_backtest(months=months)
        
        # Convert to dictionary for JSON response
        results_dict = backtest_results_to_dict(results)
        
        # Save results to file
        with open('backtest_results.json', 'w') as f:
            json.dump(results_dict, f, indent=2)
        
        logger.info(f"Backtest completed: {results.total_trades} trades, {results.total_return_pct:.2f}% return")
        
        return results_dict
    
    except Exception as e:
        logger.error(f"Backtest failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Backtest failed: {str(e)}"}
        )

@app.get("/backtest/results")
async def get_backtest_results():
    """Get latest backtest results."""
    try:
        with open('backtest_results.json', 'r') as f:
            results = json.load(f)
        return results
    
    except FileNotFoundError:
        return JSONResponse(
            status_code=404,
            content={"error": "No backtest results found"}
        )
    except Exception as e:
        logger.error(f"Error getting backtest results: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.get("/backtest/status")
async def get_backtest_status():
    """Get backtest status and progress."""
    try:
        # Check if backtest is running
        # This would need to be implemented with proper async task tracking
        return {
            "status": "idle",  # idle, running, completed, error
            "progress": 0,
            "message": "No backtest running"
        }
    
    except Exception as e:
        logger.error(f"Error getting backtest status: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

# Live Monitoring Endpoints
@app.post("/live/start")
async def start_live_monitoring_endpoint():
    """Start live pattern monitoring."""
    try:
        # Initialize broker
        from broker.dhan_adapter import DhanAdapter
        broker_adapter = DhanAdapter(settings.dhan_api_key, settings.dhan_api_secret)
        
        # Authenticate
        auth_result = await broker_adapter.authenticate()
        if not auth_result.success:
            return {"error": f"Broker authentication failed: {auth_result.error}"}
        
        # Start monitoring in background
        asyncio.create_task(start_live_monitoring(broker_adapter))
        
        logger.info("Live monitoring started")
        return {"message": "Live monitoring started successfully"}
        
    except Exception as e:
        logger.error(f"Error starting live monitoring: {e}")
        return {"error": str(e)}

@app.get("/live/alerts")
async def get_live_alerts_endpoint():
    """Get current live alerts."""
    try:
        from live_monitor import live_monitor
        
        if not live_monitor:
            return {"alerts": [], "count": 0, "timestamp": datetime.now().isoformat()}
        
        # Convert pattern alerts to the expected format
        alerts = []
        for alert in live_monitor.pattern_alerts:
            if isinstance(alert, dict):
                alerts.append(alert)
            else:
                # Convert object to dict if needed
                alerts.append({
                    "symbol": getattr(alert, 'symbol', ''),
                    "strike": getattr(alert, 'strike', 0),
                    "option_type": getattr(alert, 'option_type', ''),
                    "pattern_type": getattr(alert, 'pattern_type', ''),
                    "current_price": getattr(alert, 'current_price', 0),
                    "strength": getattr(alert, 'strength', 0),
                    "status": getattr(alert, 'status', ''),
                    "step": getattr(alert, 'step', ''),
                    "timestamp": getattr(alert, 'timestamp', '')
                })
        
        return {
            "alerts": alerts,
            "count": len(alerts),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting live alerts: {e}")
        return {"error": str(e)}

@app.get("/live/status")
async def get_live_status():
    """Get live monitoring status."""
    try:
        from live_monitor import live_monitor
        
        if live_monitor:
            return {
                "monitoring_active": live_monitor.monitoring_active,
                "contracts_count": len(live_monitor.option_contracts),
                "alerts_count": len(live_monitor.pattern_alerts),
                "last_update": datetime.now().isoformat()
            }
        else:
            return {
                "monitoring_active": False,
                "contracts_count": 0,
                "alerts_count": 0,
                "last_update": None
            }
    except Exception as e:
        logger.error(f"Error getting live status: {e}")
        return {"error": str(e)}

@app.get("/live/contracts")
async def get_contracts_status():
    """Get detailed status of all contracts being monitored."""
    try:
        from live_monitor import live_monitor
        
        if not live_monitor:
            return {"contracts": [], "count": 0}
        
        contracts_status = []
        for contract in live_monitor.option_contracts:
            # Check if this contract has any alerts
            contract_alerts = [alert for alert in live_monitor.pattern_alerts 
                             if (alert.get("symbol") == contract.symbol and 
                                 alert.get("strike") == contract.strike and 
                                 alert.get("option_type") == contract.option_type)]
            
            latest_alert = contract_alerts[-1] if contract_alerts else None
            
            contract_status = {
                "symbol": contract.symbol,
                "strike": contract.strike,
                "option_type": contract.option_type,
                "expiry": contract.expiry,
                "current_price": live_monitor._get_mock_price(contract.symbol),
                "status": latest_alert.get("status", "no_pattern") if latest_alert else "no_pattern",
                "step": latest_alert.get("step", "No pattern detected yet") if latest_alert else "No pattern detected yet",
                "strength": latest_alert.get("strength", 0) if latest_alert else 0,
                "last_update": latest_alert.get("timestamp") if latest_alert else None
            }
            contracts_status.append(contract_status)
        
        return {
            "contracts": contracts_status,
            "count": len(contracts_status),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting contracts status: {e}")
        return {"error": str(e)}

@app.get("/live/past-signals")
async def get_past_signals_endpoint():
    """Get all past signals with their outcomes."""
    try:
        from live_monitor import live_monitor
        
        if not live_monitor:
            return {"signals": [], "count": 0, "timestamp": datetime.now().isoformat()}
        
        signals = []
        for signal in live_monitor.past_signals:
            signals.append({
                "signal_id": signal.signal_id,
                "symbol": signal.symbol,
                "strike": signal.strike,
                "option_type": signal.option_type,
                "entry_price": signal.entry_price,
                "target_price": signal.target_price,
                "stop_loss_price": signal.stop_loss_price,
                "current_price": signal.current_price,
                "signal_time": signal.signal_time.isoformat(),
                "outcome": signal.outcome,
                "profit_loss_pct": signal.profit_loss_pct,
                "profit_loss_amount": signal.profit_loss_amount,
                "last_updated": signal.last_updated.isoformat() if signal.last_updated else None
            })
        
        return {
            "signals": signals,
            "count": len(signals),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting past signals: {e}")
        return {"error": str(e)}

@app.get("/live/performance")
async def get_live_performance_endpoint():
    """Get performance summary for all signals."""
    try:
        from live_monitor import live_monitor
        
        if not live_monitor:
            return {
                "total_signals": 0,
                "total_invested": 0,
                "total_current_value": 0,
                "total_pnl": 0,
                "total_pnl_pct": 0,
                "targets_hit": 0,
                "stop_losses_hit": 0,
                "still_running": 0,
                "timestamp": datetime.now().isoformat()
            }
        
        performance = live_monitor.get_performance_summary()
        performance["timestamp"] = datetime.now().isoformat()
        
        return performance
    except Exception as e:
        logger.error(f"Error getting live performance: {e}")
        return {"error": str(e)}

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize the application on startup."""
    try:
        logger.info("Starting NIFTY50 Trading System API")
        
        # Ensure directories exist
        from utils import ensure_directory
        ensure_directory(settings.trades_dir)
        ensure_directory(settings.logs_dir)
        
        logger.info("API startup completed")
    
    except Exception as e:
        logger.error(f"Error during startup: {e}")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    try:
        logger.info("Shutting down NIFTY50 Trading System API")
        
        # Stop scheduler if running
        if trading_scheduler.is_running:
            await trading_scheduler.stop()
        
        logger.info("API shutdown completed")
    
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app_backend:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )