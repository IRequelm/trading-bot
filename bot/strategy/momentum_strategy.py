import pandas as pd
import numpy as np
from dataclasses import dataclass


@dataclass
class MomentumSignal:
    side: str  # 'buy', 'sell', 'hold'
    confidence: float


def compute_momentum_signals(df: pd.DataFrame) -> MomentumSignal:
    """
    Momentum trend-following strategy:
    - Buy when momentum is strong and price is breaking up
    - Sell when momentum reverses or price breaks down
    - Uses RSI + MACD + Volume confirmation
    """
    if df.empty or len(df) < 50:
        return MomentumSignal(side="hold", confidence=0.0)
    
    prices = df['close'].astype(float)
    high = df['high'].astype(float)
    low = df['low'].astype(float)
    volume = df['volume'].astype(float)
    
    # RSI
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    # MACD
    ema_12 = prices.ewm(span=12).mean()
    ema_26 = prices.ewm(span=26).mean()
    macd_line = ema_12 - ema_26
    signal_line = macd_line.ewm(span=9).mean()
    macd_hist = macd_line - signal_line
    
    # Moving averages for trend
    sma_20 = prices.rolling(window=20).mean()
    sma_50 = prices.rolling(window=50).mean()
    
    # Volume MA
    volume_ma = volume.rolling(window=20).mean()
    volume_spike = volume > volume_ma * 1.5  # 50% above average
    
    # Get current values
    current_price = prices.iloc[-1]
    current_rsi = rsi.iloc[-1]
    current_macd = macd_line.iloc[-1]
    current_signal = signal_line.iloc[-1]
    current_hist = macd_hist.iloc[-1]
    prev_hist = macd_hist.iloc[-2] if len(macd_hist) > 1 else 0
    current_sma20 = sma_20.iloc[-1]
    current_sma50 = sma_50.iloc[-1] if len(sma_50) > 0 else current_sma20
    current_volume_spike = volume_spike.iloc[-1]
    
    # Check for NaN
    if pd.isna(current_rsi) or pd.isna(current_macd) or pd.isna(current_hist):
        return MomentumSignal(side="hold", confidence=0.0)
    
    # BUY CONDITIONS: Multiple bullish signals
    buy_signals = 0
    buy_confidence = 0.0
    
    # 1. MACD bullish crossover
    if current_macd > current_signal and current_hist > 0 and prev_hist <= 0:
        buy_signals += 1
        buy_confidence += 0.3
    
    # 2. MACD above zero with positive histogram
    if current_macd > 0 and current_hist > 0:
        buy_signals += 1
        buy_confidence += 0.2
    
    # 3. Price above SMA 20 (uptrend)
    if current_price > current_sma20:
        buy_signals += 1
        buy_confidence += 0.2
    
    # 4. RSI in bullish zone (40-70)
    if 40 < current_rsi < 70:
        buy_signals += 1
        buy_confidence += 0.2
    
    # 5. Volume confirmation
    if current_volume_spike:
        buy_signals += 1
        buy_confidence += 0.1
    
    # SELL CONDITIONS
    sell_signals = 0
    sell_confidence = 0.0
    
    # 1. MACD bearish crossover
    if current_macd < current_signal and current_hist < 0 and prev_hist >= 0:
        sell_signals += 1
        sell_confidence += 0.3
    
    # 2. MACD below zero with negative histogram
    if current_macd < 0 and current_hist < 0:
        sell_signals += 1
        sell_confidence += 0.2
    
    # 3. Price below SMA 20 (downtrend)
    if current_price < current_sma20:
        sell_signals += 1
        sell_confidence += 0.2
    
    # 4. RSI in bearish zone (30-60) or overbought
    if current_rsi < 30 or current_rsi > 70:
        sell_signals += 1
        sell_confidence += 0.2
    
    # 5. Volume confirmation
    if current_volume_spike:
        sell_signals += 1
        sell_confidence += 0.1
    
    # Generate signal (need at least 3 signals to be confident)
    if buy_signals >= 3 and buy_confidence > 0.6:
        return MomentumSignal(side="buy", confidence=min(buy_confidence, 0.95))
    elif sell_signals >= 3 and sell_confidence > 0.6:
        return MomentumSignal(side="sell", confidence=min(sell_confidence, 0.95))
    else:
        return MomentumSignal(side="hold", confidence=0.2)
