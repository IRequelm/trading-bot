# 🤖 Trading Bot Automation Setup Guide

## Overview
Once you have a profitable strategy, this guide shows how to automate it to:
1. Run 24/7 in the cloud
2. Execute trades automatically through your broker
3. Send you alerts via Telegram/Email

---

## 📊 Current Status
**Strategy**: Momentum Trend-Following (MACD + RSI + Volume + SMA)
**Best Results**: 
- ASELS.IS: +0.62% (100% win rate, 1 trade)
- AAPL: +0.28% (50% win rate, 4 trades)

**Next Steps**: Improve strategy to >2% return before automation

---

## 🚀 Part 1: Cloud Deployment (Run 24/7)

### Option A: Render (Free Tier Available)
```bash
# 1. Install Render CLI
npm install -g render-cli

# 2. Deploy
render deploy

# 3. Your bot runs at: https://your-bot.onrender.com
```

### Option B: Heroku
```bash
# 1. Install Heroku CLI
# 2. Login
heroku login

# 3. Create app
heroku create your-trading-bot

# 4. Deploy
git push heroku main

# 5. Scale worker
heroku ps:scale worker=1
```

### Option C: Railway
1. Go to railway.app
2. Connect GitHub repository
3. Click "Deploy"
4. Done! ✓

---

## 📱 Part 2: Alert System (Telegram/Email)

### Option A: Telegram Alerts (Easiest)

```python
# Add to requirements.txt
# python-telegram-bot

# bot/alerts/telegram.py
import os
import requests

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def send_telegram_alert(message):
    url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
    data = {'chat_id': TELEGRAM_CHAT_ID, 'text': message}
    requests.post(url, json=data)

# Usage:
send_telegram_alert("🚀 BUY Signal: AAPL at $150.00")
send_telegram_alert("💰 SELL Signal: AAPL at $152.00 (+1.33%)")
```

**Setup**:
1. Message @BotFather on Telegram
2. Create bot with `/newbot`
3. Get your token
4. Send message to your bot
5. Visit: `https://api.telegram.org/bot<TOKEN>/getUpdates`
6. Get your chat_id from response

### Option B: Email Alerts

```python
# bot/alerts/email.py
import smtplib
from email.mime.text import MIMEText

def send_email_alert(subject, body):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = os.getenv('EMAIL_FROM')
    msg['To'] = os.getenv('EMAIL_TO')
    
    smtp = smtplib.SMTP('smtp.gmail.com', 587)
    smtp.starttls()
    smtp.login(os.getenv('EMAIL_USER'), os.getenv('EMAIL_PASS'))
    smtp.send_message(msg)
    smtp.quit()
```

---

## 💰 Part 3: Execute Trades Automatically

### Option A: Alpaca (US Stocks, Free Paper Trading)
```python
# pip install alpaca-trade-api

import alpaca_trade_api as tradeapi

api = tradeapi.REST(
    api_key=os.getenv('ALPACA_API_KEY'),
    secret_key=os.getenv('ALPACA_SECRET_KEY'),
    base_url='https://paper-api.alpaca.markets'
)

def execute_buy(symbol, qty):
    """Buy shares"""
    order = api.submit_order(
        symbol=symbol,
        qty=qty,
        side='buy',
        type='market'
    )
    return order

def execute_sell(symbol, qty):
    """Sell shares"""
    order = api.submit_order(
        symbol=symbol,
        qty=qty,
        side='sell',
        type='market'
    )
    return order
```

**Setup**:
1. Go to https://alpaca.markets
2. Sign up for free paper trading account
3. Get API keys from dashboard
4. Enable live trading (after testing)

### Option B: Binance (Crypto)
```python
# pip install python-binance

from binance.client import Client

client = Client(
    api_key=os.getenv('BINANCE_API_KEY'),
    api_secret=os.getenv('BINANCE_SECRET_KEY')
)

def execute_buy(symbol, qty):
    order = client.create_order(
        symbol=symbol,
        side='BUY',
        type='MARKET',
        quantity=qty
    )
    return order
```

### Option C: Interactive Brokers (Professional)
```python
# pip install ib_insync

from ib_insync import *

ib = IB()
ib.connect('127.0.0.1', 7497, clientId=1)

contract = Stock('AAPL', 'SMART', 'USD')
order = MarketOrder('BUY', 10)
trade = ib.placeOrder(contract, order)
```

---

## 🔐 Part 4: Security (Environment Variables)

Create `.env` file (NEVER commit to git):
```bash
# Trading Account
ALPACA_API_KEY=your_key_here
ALPACA_SECRET_KEY=your_secret_here

# Alerts
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id

# Email
EMAIL_USER=your_email@gmail.com
EMAIL_PASS=your_password
EMAIL_FROM=bot@yourdomain.com
EMAIL_TO=you@gmail.com

# Bot Settings
BOT_ENV=production
LOG_LEVEL=INFO
```

Add to `.gitignore`:
```
.env
*.log
*.sqlite
```

---

## 📈 Part 5: Complete Integration

```python
# bot/automated_trader.py
from bot.strategy.momentum_strategy import compute_momentum_signals
from bot.alerts.telegram import send_telegram_alert
from bot.exchanges.alpaca import execute_buy, execute_sell
import time

def run_automated_trading():
    """Main trading loop"""
    symbol = 'AAPL'
    position = None
    
    while True:
        # Get signal
        signal = compute_momentum_signals(df)
        
        # Buy signal
        if signal.side == 'buy' and position is None:
            order = execute_buy(symbol, qty=10)
            send_telegram_alert(f"🚀 BUY: {symbol} at ${price}")
            position = order
        
        # Sell signal
        elif signal.side == 'sell' and position is not None:
            order = execute_sell(symbol, qty=10)
            send_telegram_alert(f"💰 SELL: {symbol} (+{profit}%)")
            position = None
        
        # Wait 5 minutes
        time.sleep(300)
```

---

## ✅ Checklist

- [ ] Strategy consistently profitable (2%+ return)
- [ ] Deploy to cloud (Render/Heroku/Railway)
- [ ] Set up alerts (Telegram/Email)
- [ ] Connect to broker API
- [ ] Add environment variables
- [ ] Test with paper trading first
- [ ] Monitor for 1 week
- [ ] Enable live trading

---

## 🎯 Recommended Path

1. **Week 1-2**: Improve strategy to 2%+ return
2. **Week 3**: Deploy to cloud, add Telegram alerts
3. **Week 4**: Connect to paper trading account
4. **Week 5**: Monitor and optimize
5. **Week 6**: Enable live trading (start small)

---

## 📞 Support

- **Strategy Issues**: Test different strategies in backtester
- **API Issues**: Check broker documentation
- **Cloud Issues**: Platform support docs

Good luck! 🚀
