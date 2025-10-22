from flask import Flask, render_template, jsonify, request
import pandas as pd
import plotly.graph_objs as go
import plotly.utils
import json
from .storage.db import Database
from .data.yahoo import fetch_candles
from .strategy.ema_rsi_atr import compute_ema_rsi_atr_signals, calculate_dynamic_stop_loss, calculate_position_size
from .backtest.simple_backtester import SimpleBacktester
from .exchange.paper import PaperExchange
from .config import settings
import threading
import time
import os

# Get the directory where this file is located
current_dir = os.path.dirname(os.path.abspath(__file__))
# Go up one level to the project root
project_root = os.path.dirname(current_dir)
# Set template folder to the templates directory in project root
template_dir = os.path.join(project_root, 'templates')

app = Flask(__name__, template_folder=template_dir)

# Global state
current_symbol = "AAPL"
current_interval = "1h"
current_exchange = None
current_data = None
bot_thread = None
bot_running = False

# Initialize with some default data
def load_initial_data():
    global current_data, current_symbol, current_interval
    try:
        current_data = fetch_candles(current_symbol, current_interval, 100)
        print(f"Loaded initial data for {current_symbol}: {len(current_data)} bars")
        if not current_data.empty:
            current_price = float(current_data.iloc[-1]["close"].iloc[0])
            print(f"Current {current_symbol} price: ${current_price:.2f}")
    except Exception as e:
        print(f"Error loading initial data: {e}")
        # Try to load BTC data as fallback
        try:
            current_symbol = "BTC-USD"
            current_data = fetch_candles(current_symbol, current_interval, 100)
            print(f"Loaded fallback BTC data: {len(current_data)} bars")
            if not current_data.empty:
                current_price = float(current_data.iloc[-1]["close"].iloc[0])
                print(f"Current BTC price: ${current_price:.2f}")
        except Exception as e2:
            print(f"Error loading fallback data: {e2}")

# Load initial data when module is imported
load_initial_data()

def run_bot_loop():
    global current_data, current_exchange, bot_running
    db = Database()
    
    while bot_running:
        try:
            df = fetch_candles(symbol=current_symbol, interval=current_interval, lookback=300)
            if df.empty:
                time.sleep(5)
                continue
            
            current_data = df
            signal = compute_ema_rsi_atr_signals(df, fast_ema=12, slow_ema=26, rsi_period=14, atr_period=14)
            last_row = df.iloc[-1]
            price = float(last_row["close"].iloc[0])
            
            # Advanced strategy with RSI filter and confidence-based execution
            executed = False
            signal_side = str(signal.side) if hasattr(signal, 'side') else "hold"
            
            # Only execute if confidence is high enough (avoid weak signals)
            min_confidence = 0.01  # Very low confidence threshold to allow more signals
            if hasattr(signal, 'confidence') and signal.confidence < min_confidence:
                signal_side = "hold"
            
            # Calculate position size based on risk management
            account_balance = current_exchange.cash + (current_exchange.position * price)
            risk_per_trade = 0.02  # 2% risk per trade
            position_size = calculate_position_size(account_balance, risk_per_trade, price, 
                                                  calculate_dynamic_stop_loss(price, signal.atr, signal_side))
            
            if signal_side == "buy" and current_exchange.position <= 0:
                if position_size > 0:
                    current_exchange.market_buy(current_symbol, qty=position_size, price=price)
                    print(f"BUY signal: Bought {position_size:.2f} {current_symbol} at ${price:.2f} (RSI: {signal.rsi:.1f}, Confidence: {signal.confidence:.2f})")
                    executed = True
            elif signal_side == "sell" and current_exchange.position > 0:
                sell_qty = min(position_size, current_exchange.position)
                if sell_qty > 0:
                    current_exchange.market_sell(current_symbol, qty=sell_qty, price=price)
                    print(f"SELL signal: Sold {sell_qty:.2f} {current_symbol} at ${price:.2f} (RSI: {signal.rsi:.1f}, Confidence: {signal.confidence:.2f})")
                    executed = True

            # Advanced risk management with ATR-based stop-loss
            if current_exchange.position > 0 and current_exchange.avg_entry_price is not None:
                entry = current_exchange.avg_entry_price
                pnl_pct = (price - entry) / entry
                
                # ATR-based dynamic stop-loss
                atr_stop_loss = calculate_dynamic_stop_loss(entry, signal.atr, "buy", atr_multiplier=2.0)
                atr_take_profit = entry + (signal.atr * 3.0)  # 3x ATR take profit
                
                # Check ATR-based stop-loss
                if price <= atr_stop_loss:
                    current_exchange.market_sell(current_symbol, qty=current_exchange.position, price=price)
                    print(f"ATR STOP-LOSS: Sold all at ${price:.2f} (entry ${entry:.2f}, ATR: {signal.atr:.2f})")
                # Check ATR-based take profit
                elif price >= atr_take_profit:
                    take_qty = max(1, current_exchange.position // 2)
                    current_exchange.market_sell(current_symbol, qty=take_qty, price=price)
                    print(f"ATR TAKE-PROFIT: Sold {take_qty} at ${price:.2f} (entry ${entry:.2f}, ATR: {signal.atr:.2f})")
                # Fallback to percentage-based if ATR is too small
                elif signal.atr < price * 0.001:  # ATR less than 0.1% of price
                    if pnl_pct <= -0.01:  # -1% stop
                        current_exchange.market_sell(current_symbol, qty=current_exchange.position, price=price)
                        print(f"PERCENTAGE STOP-LOSS: Sold all at ${price:.2f} (entry ${entry:.2f})")
                    elif pnl_pct >= 0.02:  # +2% take profit
                        take_qty = max(1, current_exchange.position // 2)
                        current_exchange.market_sell(current_symbol, qty=take_qty, price=price)
                        print(f"PERCENTAGE TAKE-PROFIT: Sold {take_qty} at ${price:.2f} (entry ${entry:.2f})")
            
            db.record_equity(timestamp=int(last_row["timestamp"]), equity=current_exchange.cash + current_exchange.position * price)
            time.sleep(5)
        except Exception as e:
            print(f"Bot error: {e}")
            time.sleep(5)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/start', methods=['POST'])
def start_bot():
    global bot_thread, bot_running, current_exchange, current_symbol, current_interval
    
    if bot_running:
        return jsonify({"status": "already_running"})
    
    data = request.json
    current_symbol = data.get('symbol', 'AAPL')
    current_interval = data.get('interval', '1h')
    
    current_exchange = PaperExchange(starting_cash=settings.paper_starting_cash)
    bot_running = True
    bot_thread = threading.Thread(target=run_bot_loop)
    bot_thread.daemon = True
    bot_thread.start()
    
    return jsonify({"status": "started"})

@app.route('/api/stop', methods=['POST'])
def stop_bot():
    global bot_running
    bot_running = False
    return jsonify({"status": "stopped"})

@app.route('/api/load_data', methods=['POST'])
def load_data():
    global current_data, current_symbol, current_interval
    
    data = request.json or {}
    symbol = data.get('symbol', current_symbol)
    interval = data.get('interval', current_interval)
    
    try:
        current_symbol = symbol
        current_interval = interval
        current_data = fetch_candles(current_symbol, current_interval, 100)
        print(f"Loaded data for {current_symbol}: {len(current_data)} bars")
        if not current_data.empty:
            current_price = float(current_data.iloc[-1]["close"].iloc[0])
            print(f"Current {current_symbol} price: ${current_price:.2f}")
    except Exception as e:
        print(f"Error loading data: {e}")
        return jsonify({"error": str(e)})
    
    return jsonify({
        "status": "data_loaded",
        "symbol": current_symbol,
        "interval": current_interval,
        "bars": len(current_data) if current_data is not None else 0
    })

@app.route('/api/status')
def get_status():
    global current_exchange, bot_running, current_data
    
    if current_exchange is None:
        return jsonify({"running": False})
    
    current_price = 0
    if current_data is not None and not current_data.empty:
        current_price = float(current_data.iloc[-1]["close"].iloc[0])
    
    total_equity = current_exchange.cash + current_exchange.position * current_price
    
    return jsonify({
        "running": bot_running,
        "symbol": current_symbol,
        "interval": current_interval,
        "cash": current_exchange.cash,
        "position": current_exchange.position,
        "current_price": current_price,
        "total_equity": total_equity,
        "trades": len(current_exchange.trades)
    })

@app.route('/api/chart')
def get_chart():
    global current_data, current_symbol, current_interval
    
    if current_data is None or current_data.empty:
        return jsonify({"error": "No data available"})
    
    # Debug: Print current price
    if not current_data.empty:
        try:
            current_price = float(current_data.iloc[-1]["close"].iloc[0])
            print(f"Chart API - Current {current_symbol} price: ${current_price:.2f}")
        except Exception:
            pass
    
    df = current_data.copy()
    
    # Handle MultiIndex columns properly
    if isinstance(df.columns, pd.MultiIndex):
        # Flatten MultiIndex columns for easier access
        df.columns = df.columns.get_level_values(0)
    
    # Calculate EMAs and RSI
    prices = df["close"].astype(float)
    ema_fast = prices.ewm(span=12).mean()
    ema_slow = prices.ewm(span=26).mean()
    
    # Calculate RSI
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    # Create TradingView-style candlestick chart
    fig = go.Figure()
    
    # Add candlesticks with TradingView colors
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name='Price',
        increasing_line_color='#26a69a',
        decreasing_line_color='#ef5350',
        increasing_fillcolor='#26a69a',
        decreasing_fillcolor='#ef5350',
        line=dict(width=1)
    ))
    
    # Add EMA lines with better styling
    fig.add_trace(go.Scatter(
        x=df.index,
        y=ema_fast,
        mode='lines',
        name='EMA 12',
        line=dict(color='#ff9800', width=2),
        opacity=0.8
    ))
    
    fig.add_trace(go.Scatter(
        x=df.index,
        y=ema_slow,
        mode='lines',
        name='EMA 26',
        line=dict(color='#2196f3', width=2),
        opacity=0.8
    ))
    
    # Add volume bars (TradingView style)
    fig.add_trace(go.Bar(
        x=df.index,
        y=df['volume'],
        name='Volume',
        marker_color='rgba(158, 158, 158, 0.3)',
        yaxis='y2',
        showlegend=False
    ))
    
    # Add buy/sell signals
    signals = []
    for i in range(1, len(df)):
        if i < 50:
            continue
        try:
            signal = compute_ema_rsi_atr_signals(df.iloc[:i+1], fast_ema=12, slow_ema=26, rsi_period=14, atr_period=14)
            # Only show signals with sufficient confidence
            if hasattr(signal, 'confidence') and signal.confidence >= 0.01:
                if signal.side == "buy":
                    # Position buy signal above the high price
                    buy_y = float(df.iloc[i]["high"]) + (float(df.iloc[i]["high"]) - float(df.iloc[i]["low"])) * 0.1
                    signals.append({"x": i, "y": buy_y, "type": "buy"})
                elif signal.side == "sell":
                    # Position sell signal below the low price
                    sell_y = float(df.iloc[i]["low"]) - (float(df.iloc[i]["high"]) - float(df.iloc[i]["low"])) * 0.1
                    signals.append({"x": i, "y": sell_y, "type": "sell"})
        except Exception as e:
            print(f"Signal calculation error at index {i}: {e}")
            continue
    
    if signals:
        buy_signals = [s for s in signals if s["type"] == "buy"]
        sell_signals = [s for s in signals if s["type"] == "sell"]
        
        if buy_signals:
            fig.add_trace(go.Scatter(
                x=[s["x"] for s in buy_signals],
                y=[s["y"] for s in buy_signals],
                mode='markers',
                name='Buy Signal',
                marker=dict(
                    color='#26a69a', 
                    size=20, 
                    symbol='triangle-up',
                    line=dict(color='white', width=3),
                    opacity=0.9
                ),
                showlegend=True
            ))
        
        if sell_signals:
            fig.add_trace(go.Scatter(
                x=[s["x"] for s in sell_signals],
                y=[s["y"] for s in sell_signals],
                mode='markers',
                name='Sell Signal',
                marker=dict(
                    color='#ef5350', 
                    size=20, 
                    symbol='triangle-down',
                    line=dict(color='white', width=3),
                    opacity=0.9
                ),
                showlegend=True
            ))
    
    # TradingView-style layout
    fig.update_layout(
        title=dict(
            text=f'{current_symbol} Trading Chart',
            font=dict(size=20, color='#1e1e1e'),
            x=0.5
        ),
        xaxis=dict(
            title='Time',
            gridcolor='#e0e0e0',
            showgrid=True,
            gridwidth=1,
            zeroline=False,
            showline=True,
            linecolor='#b0b0b0',
            linewidth=1
        ),
        yaxis=dict(
            title='Price ($)',
            gridcolor='#e0e0e0',
            showgrid=True,
            gridwidth=1,
            zeroline=False,
            showline=True,
            linecolor='#b0b0b0',
            linewidth=1,
            tickformat='$.2f',
            domain=[0.3, 1]  # Leave space for volume
        ),
        yaxis2=dict(
            title='Volume',
            gridcolor='#e0e0e0',
            showgrid=True,
            gridwidth=1,
            zeroline=False,
            showline=True,
            linecolor='#b0b0b0',
            linewidth=1,
            domain=[0, 0.25],  # Volume at bottom
            side='right'
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
        height=600,
        margin=dict(l=60, r=60, t=80, b=60),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor='rgba(255,255,255,0.8)',
            bordercolor='#e0e0e0',
            borderwidth=1
        ),
        hovermode='x unified',
        showlegend=True
    )
    
    # Debug: Print chart data info
    print(f"Chart data: {len(df)} bars, columns: {list(df.columns)}")
    print(f"Price range: {float(df['close'].min()):.2f} - {float(df['close'].max()):.2f}")
    print(f"Signals found: {len(signals)}")
    
    return app.response_class(fig.to_json(), mimetype='application/json')

@app.route('/api/test_chart')
def test_chart():
    global current_data
    if current_data is None or current_data.empty:
        return jsonify({"error": "No data available"})
    
    # Return basic chart data for testing
    df = current_data.copy()
    return jsonify({
        "bars": len(df),
        "columns": list(df.columns),
        "price_range": {
            "min": float(df['close'].min()),
            "max": float(df['close'].max())
        },
        "last_price": float(df.iloc[-1]['close'].iloc[0]),
        "sample_data": {
            "open": float(df.iloc[-1]['open'].iloc[0]),
            "high": float(df.iloc[-1]['high'].iloc[0]),
            "low": float(df.iloc[-1]['low'].iloc[0]),
            "close": float(df.iloc[-1]['close'].iloc[0]),
            "volume": float(df.iloc[-1]['volume'].iloc[0])
        }
    })

@app.route('/api/equity')
def get_equity():
    db = Database()
    conn = db.conn
    cursor = conn.cursor()
    cursor.execute("SELECT timestamp, equity FROM equity ORDER BY timestamp")
    rows = cursor.fetchall()
    
    return jsonify([{"timestamp": row[0], "equity": row[1]} for row in rows])

@app.route('/api/backtest')
def run_backtest():
    """
    Run backtest on current symbol with EMA+RSI+ATR strategy
    """
    try:
        # Get more historical data for backtesting (last 100 days)
        df = fetch_candles(symbol=current_symbol, interval=current_interval, lookback=100)
        
        if df.empty:
            return jsonify({"error": "No data available for backtesting"})
        
        # Run backtest
        backtester = SimpleBacktester(initial_capital=10000, commission=0.001)
        result = backtester.run_backtest(df)
        
        return jsonify({
            "success": True,
            "results": {
                "total_return": result.total_return,
                "annual_return": result.annual_return,
                "sharpe_ratio": result.sharpe_ratio,
                "max_drawdown": result.max_drawdown,
                "win_rate": result.win_rate,
                "total_trades": result.total_trades,
                "profitable_trades": result.profitable_trades,
                "losing_trades": result.losing_trades,
                "avg_win": result.avg_win,
                "avg_loss": result.avg_loss,
                "profit_factor": result.profit_factor,
                "final_equity": 10000 * (1 + result.total_return),
                "symbol": current_symbol,
                "period": f"{df.index[0]} to {df.index[-1]}"
            }
        })
        
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
