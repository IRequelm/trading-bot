import pandas as pd
import numpy as np
from dataclasses import dataclass


@dataclass
class VWAPSignal:
    side: str  # 'buy', 'sell', 'hold'
    confidence: float


def compute_vwap_signals(df: pd.DataFrame) -> VWAPSignal:
    """
    VWAP (Volume-Weighted Average Price) strategy for day trading:
    - Buy when price is below VWAP (expecting it to bounce back up)
    - Sell when price is above VWAP (expecting it to fall back down)
    - Works great on intraday charts
    """
    if df.empty or len(df) < 2:
        return VWAPSignal(side="hold", confidence=0.0)
    
    # Calculate VWAP
    high = df['high'].astype(float)
    low = df['low'].astype(float)
    close = df['close'].astype(float)
    volume = df['volume'].astype(float)
    
    # Typical Price
    typical_price = (high + low + close) / 3
    
    # VWAP
    vwap = (typical_price * volume).cumsum() / volume.cumsum()
    current_vwap = vwap.iloc[-1]
    current_price = close.iloc[-1]
    
    # Calculate distance from VWAP as percentage
    distance_pct = (current_price - current_vwap) / current_vwap * 100
    
    # Use 0.3% threshold for intraday trading
    threshold = 0.3
    
    # Buy when price is below VWAP (oversold)
    if distance_pct < -threshold:
        # Stronger signal the further below VWAP
        confidence = min(abs(distance_pct) / 2, 0.95)
        return VWAPSignal(side="buy", confidence=confidence)
    
    # Sell when price is above VWAP (overbought)
    elif distance_pct > threshold:
        # Stronger signal the further above VWAP
        confidence = min(abs(distance_pct) / 2, 0.95)
        return VWAPSignal(side="sell", confidence=confidence)
    
    else:
        return VWAPSignal(side="hold", confidence=0.1)
