import pandas as pd
import numpy as np
from dataclasses import dataclass


@dataclass
class SimpleEMASignal:
    side: str  # 'buy', 'sell', 'hold'
    confidence: float


def compute_simple_ema_signals(df: pd.DataFrame, fast_ema: int = 12, slow_ema: int = 26) -> SimpleEMASignal:
    """
    Simple EMA crossover strategy without RSI filters
    """
    if df.empty or len(df) < max(fast_ema, slow_ema) + 1:
        return SimpleEMASignal(side="hold", confidence=0.0)

    # Calculate EMAs
    prices = df["close"].astype(float)
    ema_fast = prices.ewm(span=fast_ema).mean()
    ema_slow = prices.ewm(span=slow_ema).mean()
    
    # Get current and previous values
    current_ema_fast = ema_fast.iloc[-1]
    current_ema_slow = ema_slow.iloc[-1]
    prev_ema_fast = ema_fast.iloc[-2]
    prev_ema_slow = ema_slow.iloc[-2]
    
    # Check for NaN values
    if pd.isna(current_ema_fast) or pd.isna(current_ema_slow) or pd.isna(prev_ema_fast) or pd.isna(prev_ema_slow):
        return SimpleEMASignal(side="hold", confidence=0.0)
    
    # EMA crossover logic
    ema_bullish = prev_ema_fast <= prev_ema_slow and current_ema_fast > current_ema_slow
    ema_bearish = prev_ema_fast >= prev_ema_slow and current_ema_fast < current_ema_slow
    
    # Calculate confidence based on EMA separation
    ema_separation = abs(current_ema_fast - current_ema_slow) / current_ema_slow
    confidence = min(ema_separation * 20, 1.0)  # Scale confidence
    
    # Generate signals
    if ema_bullish:
        return SimpleEMASignal(side="buy", confidence=confidence)
    elif ema_bearish:
        return SimpleEMASignal(side="sell", confidence=confidence)
    else:
        return SimpleEMASignal(side="hold", confidence=confidence)
