# Trading Bot with Backtesting

A sophisticated trading bot with multiple strategies, real-time monitoring, and comprehensive backtesting capabilities.

## 🚀 Features

- **Multiple Trading Strategies**: SMA, EMA+RSI+ATR, Pivot Points, Price Action
- **Real-time Web Dashboard**: Live charts, equity tracking, trade monitoring
- **Comprehensive Backtesting**: Historical performance analysis with detailed metrics
- **Paper Trading**: Risk-free simulation with realistic market conditions
- **Portfolio Management**: Position sizing, stop-loss, take-profit
- **Multi-Asset Support**: Cryptocurrencies, US Stocks, BIST100 stocks

## 📋 Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

## 🛠️ Installation

### 1. Clone or Download the Project
```bash
# If using git
git clone <repository-url>
cd Bot

# Or download and extract the project files
```

### 2. Create Virtual Environment
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS/Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

## 🚀 Quick Start

### 1. Start the Web Interface
```bash
python main.py web
```

### 2. Open Your Browser
Navigate to: `http://localhost:5000`

### 3. Configure Your Trading
- Select a symbol (BTC-USD, AAPL, etc.)
- Choose time interval (1h, 1d, etc.)
- Load data and start the bot
- Run backtests to analyze performance

## 📊 Usage Guide

### Web Dashboard
1. **Load Data**: Select symbol and interval, click "Load Data"
2. **Start Bot**: Click "Start Bot" to begin live trading simulation
3. **Monitor Performance**: Watch real-time charts and equity curve
4. **Run Backtests**: Click "📊 Backtest Strategy" to analyze historical performance

### Available Symbols
- **Cryptocurrencies**: BTC-USD, ETH-USD, ADA-USD, etc.
- **US Stocks**: AAPL, MSFT, GOOGL, TSLA, etc.
- **BIST100 Stocks**: AKBNK, THYAO, TUPRS, etc.

### Trading Strategies
- **SMA Crossover**: Simple moving average crossovers
- **EMA+RSI+ATR**: Advanced strategy with risk management
- **Pivot Points**: Support/resistance breakout strategy
- **Price Action**: Momentum and volatility-based signals

## 🔧 Configuration

### Environment Variables (Optional)
Create a `.env` file for custom settings:
```env
FLASK_DEBUG=True
DEFAULT_SYMBOL=BTC-USD
DEFAULT_INTERVAL=1h
```

### Database (Optional)
The bot uses SQLite by default. For production, you can configure PostgreSQL or MySQL in `bot/config.py`.

## 📁 Project Structure

```
Bot/
├── main.py                 # Entry point
├── requirements.txt        # Dependencies
├── README.md              # This file
├── bot/
│   ├── web_ui.py          # Flask web interface
│   ├── cli.py             # Command line interface
│   ├── config.py          # Configuration settings
│   ├── data/
│   │   └── yahoo.py       # Data fetching
│   ├── strategy/
│   │   ├── sma.py         # SMA strategy
│   │   ├── ema_rsi_atr.py # Advanced strategy
│   │   ├── pivot_strategy.py # Pivot strategies
│   │   └── price_action.py # Price action strategies
│   ├── exchange/
│   │   └── paper.py       # Paper trading
│   ├── backtest/
│   │   ├── backtester.py  # Advanced backtester
│   │   └── simple_backtester.py # Simple backtester
│   └── storage/
│       └── db.py          # Database operations
└── templates/
    └── index.html         # Web interface template
```

## 🎯 Key Features Explained

### Real-time Trading
- **Paper Trading**: Simulates real market conditions without risk
- **Position Management**: Automatic position sizing and risk management
- **Signal Generation**: Multiple strategies generate buy/sell signals
- **Performance Tracking**: Real-time P&L and equity curve

### Backtesting
- **Historical Analysis**: Test strategies on past data
- **Performance Metrics**: Win rate, Sharpe ratio, max drawdown
- **Risk Analysis**: Profit factor, average win/loss
- **Strategy Comparison**: Compare different approaches

### Web Interface
- **Live Charts**: Real-time price charts with technical indicators
- **Trade Signals**: Visual buy/sell signals on charts
- **Portfolio Overview**: Current positions and performance
- **Backtest Results**: Comprehensive performance analysis

## 🚨 Important Notes

### Data Sources
- **Yahoo Finance**: Free but has rate limits
- **Alternative Sources**: Can be configured for other data providers
- **Offline Mode**: Limited functionality without internet

### Risk Management
- **Paper Trading Only**: No real money at risk
- **Educational Purpose**: For learning and strategy development
- **Production Use**: Requires additional security and risk management

## 🔧 Troubleshooting

### Common Issues

1. **"No data available"**
   - Check internet connection
   - Try different symbols
   - Wait for rate limit reset

2. **"Module not found"**
   - Ensure virtual environment is activated
   - Run `pip install -r requirements.txt`

3. **"Port already in use"**
   - Change port in `main.py` or kill existing process
   - Use `netstat -ano | findstr :5000` (Windows) to find process

### Performance Tips
- Use longer intervals (1d) for faster backtesting
- Limit historical data for quicker analysis
- Close browser tabs to reduce memory usage

## 📈 Next Steps

1. **Strategy Development**: Create custom trading strategies
2. **Data Integration**: Add more data sources
3. **Risk Management**: Implement advanced position sizing
4. **Deployment**: Set up for production use
5. **Monitoring**: Add alerts and notifications

## 🤝 Contributing

Feel free to:
- Add new trading strategies
- Improve the web interface
- Add more data sources
- Enhance backtesting capabilities

## 📄 License

This project is for educational purposes. Use at your own risk.

---

**Happy Trading! 📈🚀**