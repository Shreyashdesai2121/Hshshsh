# NIFTY50 Trading System

A complete algorithmic trading system for NIFTY50 options implementing Channel Breakout + No-Sure-Thing (KST) strategy with a professional dashboard.

## 🚀 Features

- **Advanced Strategy**: Channel detection with KST confirmation for high-probability trades
- **Dual Broker Support**: Dhan (primary) and Zerodha (alternative) integration
- **Real-time Dashboard**: Modern React + Tailwind CSS interface
- **Risk Management**: Stop-loss, target-based exits, position sizing
- **Dry Run Mode**: Test strategy without real money
- **WebSocket Updates**: Real-time data streaming
- **Comprehensive Logging**: Detailed logs and performance metrics
- **Docker Support**: Easy deployment with Docker Compose

## 📋 Strategy Overview

### Core Logic
1. **Channel Detection**: Identifies parallel channels in 20-minute NIFTY50 option data
2. **KST Confirmation**: Uses 2-hour No-Sure-Thing indicator for signal validation
3. **Opposite Conditions**: Requires bullish call channel + bearish put channel
4. **Breakout Entry**: Enters on first 20-minute candle close outside channel
5. **Fibonacci Targets**: Dynamic target selection based on profit potential
6. **Channel Re-entry Stop**: Exits when price returns inside channel

### Key Parameters
- **Timeframe**: 20-minute candles for channel detection
- **KST Timeframe**: 2-hour candles for confirmation
- **Minimum Channel Duration**: 7 calendar days
- **Minimum Touches**: 2 per channel line
- **Profit Threshold**: 50% for target selection

## 🛠️ Installation

### Prerequisites
- Python 3.11+
- Node.js 18+
- Git

### Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd nifty50-trading-system
   ```

2. **Backend Setup**
   ```bash
   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Copy environment file
   cp .env.example .env
   ```

3. **Frontend Setup**
   ```bash
   cd frontend
   npm install
   ```

4. **Configure Environment**
   Edit `.env` file with your broker API keys:
   ```env
   # TODO: Replace with actual keys
   DHAN_API_KEY=your_dhan_api_key_here
   DHAN_API_SECRET=your_dhan_api_secret_here
   ZERODHA_API_KEY=your_zerodha_api_key_here
   ZERODHA_API_SECRET=your_zerodha_api_secret_here
   
   # Trading configuration
   MODE=dry_run
   QUANTITY=1
   ONE_TRADE_PER_DAY=true
   ```

## 🚀 Running the System

### Development Mode

1. **Start Backend**
   ```bash
   uvicorn app_backend:app --host 127.0.0.1 --port 8000 --reload
   ```

2. **Start Frontend** (in new terminal)
   ```bash
   cd frontend
   npm run dev
   ```

3. **Access Dashboard**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### Docker Mode

```bash
# Build and start all services
docker-compose up --build

# Run in background
docker-compose up -d
```

## 📊 Dashboard Features

### Control Panel
- **Start/Stop Strategy**: One-click strategy control
- **Mode Toggle**: Switch between dry run and live trading
- **Force Close**: Emergency position closure
- **Settings**: Configure quantity, trading limits

### Real-time Metrics
- **Today's P&L**: Current day profit/loss
- **Open Positions**: Active trades count
- **Trades Today**: Number of completed trades
- **Win Rate**: Success percentage

### Data Tables
- **Positions Table**: Live position tracking
- **Trades History**: Complete trade log
- **System Logs**: Real-time log viewer
- **Performance Chart**: P&L visualization

## 🔧 Configuration

### Backend Configuration (`config.py`)

```python
# Trading Parameters
MODE = "dry_run"  # or "live"
QUANTITY = 1
ONE_TRADE_PER_DAY = True
TRADING_START = "09:15"
TRADING_END = "15:30"

# Strategy Parameters
SCHEDULER_CANDLE_MINUTES = 20
NST_TIMEFRAME = "2h"
CHANNEL_MIN_DAYS = 7
CHANNEL_MIN_TOUCHES = 2
PROFIT_THRESHOLD_PERCENT = 50.0
```

### Broker Configuration

#### Dhan Integration
1. Get API credentials from Dhan
2. Update `.env` with your keys
3. Set `USE_DHAN=true` in config

#### Zerodha Integration
1. Get API credentials from Zerodha
2. Update `.env` with your keys
3. Set `USE_ZERODHA=true` in config

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_utils.py

# Run with coverage
pytest --cov=. --cov-report=html
```

## 📈 API Endpoints

### Strategy Control
- `POST /start_strategy` - Start trading strategy
- `POST /stop_strategy` - Stop trading strategy
- `GET /status` - Get system status

### Data Access
- `GET /positions` - Get open positions
- `GET /trades` - Get trade history
- `GET /performance` - Get performance metrics
- `GET /signals` - Get recent signals

### System
- `GET /logs` - Get system logs
- `GET /health` - Health check
- `WebSocket /ws` - Real-time updates

## 🔒 Safety Features

### Dry Run Mode
- **No Real Orders**: All trades are simulated
- **Full Logging**: Complete audit trail
- **Safe Testing**: Validate strategy without risk

### Risk Controls
- **Margin Check**: Validates available funds
- **Position Limits**: Configurable position sizing
- **Stop Loss**: Automatic loss protection
- **Trading Hours**: Respects market timings

### Before Going Live
1. ✅ Test in dry run for 3+ days
2. ✅ Verify broker API connectivity
3. ✅ Check margin requirements
4. ✅ Review strategy parameters
5. ✅ Monitor system performance

## 🐛 Troubleshooting

### Common Issues

**Backend won't start**
```bash
# Check Python version
python --version  # Should be 3.11+

# Check dependencies
pip install -r requirements.txt

# Check logs
tail -f logs/strategy.log
```

**Frontend won't connect**
```bash
# Check if backend is running
curl http://localhost:8000/health

# Check CORS settings in app_backend.py
```

**No data from broker**
- Verify API keys in `.env`
- Check broker API status
- Review broker adapter logs

### Logs Location
- **Strategy Logs**: `logs/strategy.log`
- **System State**: `state.json`
- **Trade Records**: `trades/` directory

## 📚 Architecture

### Backend Components
- **Data Engine**: Market data fetching and caching
- **Analysis Engine**: Technical analysis and signal generation
- **Execution Engine**: Order management and position tracking
- **Scheduler**: Strategy orchestration and timing
- **Broker Adapters**: Dhan and Zerodha integration

### Frontend Components
- **Dashboard**: Main control interface
- **WebSocket Client**: Real-time data updates
- **Charts**: Performance visualization
- **Tables**: Data display and management

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This software is for educational and research purposes only. Trading involves substantial risk of loss and is not suitable for all investors. Past performance is not indicative of future results. Always test thoroughly in dry run mode before live trading.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section
2. Review the logs
3. Create an issue on GitHub
4. Check broker API documentation

---

**Happy Trading! 📈**