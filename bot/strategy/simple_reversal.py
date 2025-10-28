import pandas as pd
import numpy as np
from dataclasses import dataclass


@dataclass
class ReversalSignal:
    side: str  # 'buy', 'sell', 'hold'
    confidence: float


def compute_mean_reversion_signals(df: pd.DataFrame) -> ReversalSignal:
    """
    Simple mean reversion strategy for day trading:
    - Buy when price is significantly below recent average
    - Sell when price is significantly above recent average
    - Works on 5m charts
    """
    if df.empty or len(df) < 20:
        return ReversalSignal(side="hold", confidence=0.0)
    
    # Get recent prices
    prices = df["close"].astype(float)
    
    # Calculate 20-period moving average
    ma_20 = prices.tail(20).mean()
    current_price = prices.iloc[-1]
    
    # Calculate distance from mean
    distance = (current_price - ma_20) / ma_20
    
    # Calculate RSI for confirmation
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    current_rsi = rsi.iloc[-1] if not rsi.empty else 50
    
    # Mean reversion signals
    # Buy when price is below mean and RSI is not oversold (avoid catching falling knives)
    if distance < -0.015 and current_rsi < 50:  # 1.5% below mean
        return ReversalSignal(side="buy", confidence=0.75)
    
    # Sell when price is above mean and RSI is not overbought
    elif distance > 0.015 and current_rsi > 50:  # 1.5% above mean
        return ReversalSignal(side="sell", confidence=0.75)
    
    else:
        return ReversalSignal(side="hold", confidence=0.1)
