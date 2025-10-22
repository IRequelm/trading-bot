import pandas as pd
import numpy as np
from dataclasses import dataclass


@dataclass
class SimpleSignal:
    side: str  # 'buy', 'sell', 'hold'
    confidence: float


def compute_simple_signals(df: pd.DataFrame) -> SimpleSignal:
    """
    Ultra-simple strategy that will definitely generate signals
    """
    if df.empty or len(df) < 2:
        return SimpleSignal(side="hold", confidence=0.0)

    prices = df["close"].astype(float)
    current_price = prices.iloc[-1]
    prev_price = prices.iloc[-2]
    
    # Simple price change strategy
    price_change = (current_price - prev_price) / prev_price
    
    # Generate signals on any significant movement
    if price_change > 0.005:  # Price up more than 0.5%
        return SimpleSignal(side="buy", confidence=0.5)
    elif price_change < -0.005:  # Price down more than 0.5%
        return SimpleSignal(side="sell", confidence=0.5)
    else:
        return SimpleSignal(side="hold", confidence=0.1)


def compute_alternating_signals(df: pd.DataFrame) -> SimpleSignal:
    """
    Alternating buy/sell strategy for testing
    """
    if df.empty:
        return SimpleSignal(side="hold", confidence=0.0)
    
    # Alternate between buy and sell every few bars
    index = len(df)
    if index % 10 == 0:
        return SimpleSignal(side="buy", confidence=0.8)
    elif index % 10 == 5:
        return SimpleSignal(side="sell", confidence=0.8)
    else:
        return SimpleSignal(side="hold", confidence=0.1)
