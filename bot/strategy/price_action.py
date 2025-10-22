import pandas as pd
import numpy as np
from dataclasses import dataclass


@dataclass
class PriceActionSignal:
    side: str  # 'buy', 'sell', 'hold'
    confidence: float


def compute_price_action_signals(df: pd.DataFrame) -> PriceActionSignal:
    """
    Simple price action strategy that will definitely generate signals
    """
    if df.empty or len(df) < 3:
        return PriceActionSignal(side="hold", confidence=0.0)

    # Get recent prices
    prices = df["close"].astype(float)
    highs = df["high"].astype(float)
    lows = df["low"].astype(float)
    
    current_price = prices.iloc[-1]
    prev_price = prices.iloc[-2]
    prev2_price = prices.iloc[-3]
    
    # Calculate price change
    price_change = (current_price - prev_price) / prev_price
    prev_change = (prev_price - prev2_price) / prev2_price
    
    # Simple momentum strategy
    if price_change > 0.01:  # Price up more than 1%
        return PriceActionSignal(side="buy", confidence=0.7)
    elif price_change < -0.01:  # Price down more than 1%
        return PriceActionSignal(side="sell", confidence=0.7)
    elif price_change > 0.005 and prev_change > 0.005:  # Two consecutive up moves
        return PriceActionSignal(side="buy", confidence=0.6)
    elif price_change < -0.005 and prev_change < -0.005:  # Two consecutive down moves
        return PriceActionSignal(side="sell", confidence=0.6)
    else:
        return PriceActionSignal(side="hold", confidence=0.1)


def compute_volatility_breakout_signals(df: pd.DataFrame, period: int = 10) -> PriceActionSignal:
    """
    Volatility breakout strategy
    """
    if df.empty or len(df) < period + 1:
        return PriceActionSignal(side="hold", confidence=0.0)

    prices = df["close"].astype(float)
    current_price = prices.iloc[-1]
    
    # Calculate volatility
    returns = prices.pct_change().dropna()
    if len(returns) < period:
        return PriceActionSignal(side="hold", confidence=0.0)
    
    volatility = returns.tail(period).std()
    mean_return = returns.tail(period).mean()
    
    # Current return
    current_return = (current_price - prices.iloc[-2]) / prices.iloc[-2]
    
    # Breakout signals
    if current_return > mean_return + 2 * volatility:  # Strong positive breakout
        return PriceActionSignal(side="buy", confidence=0.8)
    elif current_return < mean_return - 2 * volatility:  # Strong negative breakout
        return PriceActionSignal(side="sell", confidence=0.8)
    elif current_return > mean_return + volatility:  # Moderate positive
        return PriceActionSignal(side="buy", confidence=0.6)
    elif current_return < mean_return - volatility:  # Moderate negative
        return PriceActionSignal(side="sell", confidence=0.6)
    else:
        return PriceActionSignal(side="hold", confidence=0.1)


def compute_simple_trend_signals(df: pd.DataFrame, period: int = 5) -> PriceActionSignal:
    """
    Simple trend following strategy
    """
    if df.empty or len(df) < period + 1:
        return PriceActionSignal(side="hold", confidence=0.0)

    prices = df["close"].astype(float)
    current_price = prices.iloc[-1]
    period_ago_price = prices.iloc[-period-1]
    
    # Calculate trend
    trend = (current_price - period_ago_price) / period_ago_price
    
    # Generate signals based on trend strength
    if trend > 0.05:  # Strong uptrend (5%+)
        return PriceActionSignal(side="buy", confidence=0.8)
    elif trend < -0.05:  # Strong downtrend (-5%+)
        return PriceActionSignal(side="sell", confidence=0.8)
    elif trend > 0.02:  # Moderate uptrend (2%+)
        return PriceActionSignal(side="buy", confidence=0.6)
    elif trend < -0.02:  # Moderate downtrend (-2%+)
        return PriceActionSignal(side="sell", confidence=0.6)
    else:
        return PriceActionSignal(side="hold", confidence=0.1)
