import pandas as pd
import numpy as np
from dataclasses import dataclass


@dataclass
class BasicMASignal:
    side: str  # 'buy', 'sell', 'hold'


def compute_basic_ma_signals(df: pd.DataFrame, fast_period: int = 5, slow_period: int = 10) -> BasicMASignal:
    """
    Very basic moving average crossover strategy that will definitely generate signals
    """
    if df.empty or len(df) < slow_period + 1:
        return BasicMASignal(side="hold")

    # Calculate simple moving averages
    prices = df["close"].astype(float)
    ma_fast = prices.rolling(window=fast_period).mean()
    ma_slow = prices.rolling(window=slow_period).mean()
    
    # Get current and previous values
    if len(df) < 2:
        return BasicMASignal(side="hold")
        
    current_fast = ma_fast.iloc[-1]
    current_slow = ma_slow.iloc[-1]
    prev_fast = ma_fast.iloc[-2]
    prev_slow = ma_slow.iloc[-2]
    
    # Check for NaN values
    if pd.isna(current_fast) or pd.isna(current_slow) or pd.isna(prev_fast) or pd.isna(prev_slow):
        return BasicMASignal(side="hold")
    
    # Simple crossover logic
    if prev_fast <= prev_slow and current_fast > current_slow:
        return BasicMASignal(side="buy")
    elif prev_fast >= prev_slow and current_fast < current_slow:
        return BasicMASignal(side="sell")
    else:
        return BasicMASignal(side="hold")
