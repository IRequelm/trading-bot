import pandas as pd
import numpy as np
from dataclasses import dataclass


@dataclass
class ScalpSignal:
    side: str  # 'buy', 'sell', 'hold'
    confidence: float


def compute_ml_scalping_signals(df: pd.DataFrame) -> ScalpSignal:
    """
    Aggressive scalping strategy for 5m charts
    Uses simple pattern recognition to catch quick price movements
    """
    if df.empty or len(df) < 20:
        return ScalpSignal(side="hold", confidence=0.0)
    
    prices = df['close'].astype(float)
    
    # Simple indicators
    sma_5 = prices.rolling(5).mean()
    sma_10 = prices.rolling(10).mean()
    ema_9 = prices.ewm(span=9).mean()
    
    # RSI
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    # Price momentum
    momentum = prices.pct_change(3)
    
    # Volume
    volume = df['volume'].astype(float)
    volume_sma = volume.rolling(10).mean()
    volume_spike = volume > volume_sma * 1.2
    
    # Current values
    current_price = prices.iloc[-1]
    current_sma5 = sma_5.iloc[-1]
    current_sma10 = sma_10.iloc[-1]
    current_ema9 = ema_9.iloc[-1]
    current_rsi = rsi.iloc[-1]
    current_momentum = momentum.iloc[-1]
    current_vol_spike = volume_spike.iloc[-1] if len(volume_spike) > 0 else False
    
    # Check NaN
    if pd.isna(current_sma5) or pd.isna(current_rsi):
        return ScalpSignal(side="hold", confidence=0.0)
    
    # AGGRESSIVE BUY CONDITIONS (multiple will trigger frequently)
    buy_score = 0
    
    # 1. Price crosses above MA
    if current_price > current_sma5 and prices.iloc[-2] <= sma_5.iloc[-2]:
        buy_score += 2
    
    # 2. MAs aligned bullishly
    if current_sma5 > current_sma10:
        buy_score += 1
    
    # 3. RSI not overbought
    if 30 < current_rsi < 70:
        buy_score += 1
    
    # 4. Positive momentum
    if current_momentum > 0.001:  # 0.1% or more
        buy_score += 2
    
    # 5. Volume confirmation
    if current_vol_spike:
        buy_score += 1
    
    # SELL CONDITIONS
    sell_score = 0
    
    # 1. Price crosses below MA
    if current_price < current_sma5 and prices.iloc[-2] >= sma_5.iloc[-2]:
        sell_score += 2
    
    # 2. MAs aligned bearishly
    if current_sma5 < current_sma10:
        sell_score += 1
    
    # 3. RSI overbought or oversold
    if current_rsi > 70 or current_rsi < 30:
        sell_score += 1
    
    # 4. Negative momentum
    if current_momentum < -0.001:
        sell_score += 2
    
    # 5. Volume confirmation
    if current_vol_spike:
        sell_score += 1
    
    # Generate signals (lower threshold = more trades)
    if buy_score >= 3:
        return ScalpSignal(side="buy", confidence=min(buy_score / 7, 0.9))
    elif sell_score >= 3:
        return ScalpSignal(side="sell", confidence=min(sell_score / 7, 0.9))
    else:
        # Even if score is lower, still trade if some conditions met
        if buy_score >= 2:
            return ScalpSignal(side="buy", confidence=0.5)
        elif sell_score >= 2:
            return ScalpSignal(side="sell", confidence=0.5)
        else:
            return ScalpSignal(side="hold", confidence=0.2)
