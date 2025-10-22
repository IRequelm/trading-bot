# 🤖 Trading Bot by IRequelm

A sophisticated trading bot with multiple strategies, real-time monitoring, and comprehensive backtesting capabilities.

## 🚀 Quick Start

### Option 1: GitHub Codespaces (Recommended)
1. **Go to**: [github.com/IRequelm/trading-bot](https://github.com/IRequelm/trading-bot)
2. **Click**: "Code" → "Codespaces" → "Create codespace"
3. **Wait**: For environment to load (2-3 minutes)
4. **Run**: `python main.py web`
5. **Open**: Browser to `http://localhost:5000`

### Option 2: Local Setup
```bash
# Clone the repository
git clone https://github.com/IRequelm/trading-bot.git
cd trading-bot

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the bot
python main.py web
```

## 📊 Features

- **🎯 Multiple Strategies**: SMA, EMA+RSI+ATR, Pivot Points, Price Action
- **📈 Real-time Dashboard**: Live charts, equity tracking, trade monitoring
- **🔬 Backtesting**: Historical performance analysis with detailed metrics
- **💰 Paper Trading**: Risk-free simulation with realistic conditions
- **🌍 Multi-Asset**: Cryptocurrencies, US Stocks, BIST100 stocks
- **☁️ Cloud Ready**: Work from any computer via GitHub Codespaces

## 🎮 How to Use

### 1. Load Data
- Select symbol (BTC-USD, AAPL, etc.)
- Choose interval (1h, 1d, etc.)
- Click "Load Data"

### 2. Start Trading
- Click "Start Bot" to begin simulation
- Watch real-time charts and signals
- Monitor performance metrics

### 3. Run Backtests
- Click "📊 Backtest Strategy"
- Analyze historical performance
- Compare different strategies

## 📈 Available Strategies

### Simple Moving Average (SMA)
- **Logic**: Buy when fast MA crosses above slow MA
- **Best for**: Trend following, stable markets
- **Parameters**: 5-period fast, 20-period slow

### EMA + RSI + ATR
- **Logic**: Advanced strategy with risk management
- **Best for**: Volatile markets, professional trading
- **Features**: Dynamic stop-loss, position sizing

### Pivot Points
- **Logic**: Support/resistance breakout strategy
- **Best for**: Range-bound markets, day trading
- **Features**: Multiple pivot calculations

### Price Action
- **Logic**: Momentum and volatility-based signals
- **Best for**: Quick scalping, high-frequency trading
- **Features**: Volatility breakouts, trend following

## 🌐 Cloud Access

### GitHub Codespaces
- **URL**: [github.com/IRequelm/trading-bot](https://github.com/IRequelm/trading-bot)
- **Access**: Click "Code" → "Codespaces" → "Create codespace"
- **Features**: Full VS Code in browser, 120 hours/month free

### Alternative Platforms
- **Replit**: [replit.com](https://replit.com) - Upload and run instantly
- **Google Colab**: [colab.research.google.com](https://colab.research.google.com) - For testing
- **GitPod**: [gitpod.io](https://gitpod.io) - Professional IDE

## 📊 Performance Metrics

The backtesting system provides comprehensive analysis:

- **Total Return**: Overall profit/loss percentage
- **Win Rate**: Percentage of profitable trades
- **Sharpe Ratio**: Risk-adjusted returns
- **Max Drawdown**: Worst loss period
- **Profit Factor**: Gains vs losses ratio
- **Average Win/Loss**: Per-trade performance

## 🔧 Configuration

### Environment Variables
Create `.env` file for custom settings:
```env
FLASK_DEBUG=True
DEFAULT_SYMBOL=BTC-USD
DEFAULT_INTERVAL=1h
```

### Strategy Parameters
Modify strategy parameters in:
- `bot/strategy/sma.py` - SMA settings
- `bot/strategy/ema_rsi_atr.py` - Advanced strategy
- `bot/strategy/pivot_strategy.py` - Pivot settings
- `bot/strategy/price_action.py` - Price action settings

## 🚨 Important Notes

### Data Sources
- **Yahoo Finance**: Free but has rate limits
- **Rate Limits**: Wait a few minutes if you hit limits
- **Offline Mode**: Limited functionality without internet

### Risk Management
- **Paper Trading Only**: No real money at risk
- **Educational Purpose**: For learning and strategy development
- **Production Use**: Requires additional security measures

## 🛠️ Troubleshooting

### Common Issues
1. **"No data available"**: Check internet connection, try different symbols
2. **"Module not found"**: Run `pip install -r requirements.txt`
3. **"Port already in use"**: Change port or kill existing process
4. **"Rate limited"**: Wait a few minutes and try again

### Getting Help
- **GitHub Issues**: Create issues in the repository
- **Documentation**: Check this README and code comments
- **Community**: Stack Overflow, Reddit trading communities

## 📈 Next Steps

1. **Strategy Development**: Create custom trading strategies
2. **Data Integration**: Add more data sources (Alpha Vantage, IEX Cloud)
3. **Risk Management**: Implement advanced position sizing
4. **Deployment**: Set up for production use
5. **Monitoring**: Add alerts and notifications

## 🤝 Contributing

Feel free to:
- Add new trading strategies
- Improve the web interface
- Add more data sources
- Enhance backtesting capabilities
- Fix bugs and improve performance

## 📄 License

This project is for educational purposes. Use at your own risk.

---

**Happy Trading! 📈🚀**

*Created by IRequelm - Access from anywhere via GitHub Codespaces*
