import pandas as pd
import numpy as np
from dataclasses import dataclass


@dataclass
class PivotSignal:
    side: str  # 'buy', 'sell', 'hold'
    confidence: float


def compute_pivot_signals(df: pd.DataFrame, lookback: int = 5) -> PivotSignal:
    """
    Pivot point strategy based on support/resistance levels
    """
    if df.empty or len(df) < lookback * 2:
        return PivotSignal(side="hold", confidence=0.0)

    # Get recent data
    recent_data = df.tail(lookback * 2)
    prices = recent_data["close"].astype(float)
    highs = recent_data["high"].astype(float)
    lows = recent_data["low"].astype(float)
    
    # Calculate pivot points
    current_price = prices.iloc[-1]
    current_high = highs.iloc[-1]
    current_low = lows.iloc[-1]
    
    # Find recent highs and lows for pivot calculation
    recent_highs = highs.tail(lookback)
    recent_lows = lows.tail(lookback)
    
    # Calculate pivot levels
    pivot_high = recent_highs.max()
    pivot_low = recent_lows.min()
    pivot_mid = (pivot_high + pivot_low) / 2
    
    # Calculate confidence based on how close price is to pivot levels
    distance_to_high = abs(current_price - pivot_high) / pivot_high
    distance_to_low = abs(current_price - pivot_low) / pivot_low
    distance_to_mid = abs(current_price - pivot_mid) / pivot_mid
    
    # Generate signals based on pivot levels
    if current_price > pivot_high * 1.001:  # Price breaks above resistance
        confidence = min(1.0 - distance_to_high, 0.8)  # Higher confidence for clean breaks
        return PivotSignal(side="buy", confidence=confidence)
    elif current_price < pivot_low * 0.999:  # Price breaks below support
        confidence = min(1.0 - distance_to_low, 0.8)
        return PivotSignal(side="sell", confidence=confidence)
    elif current_price > pivot_mid * 1.002:  # Price above mid-level
        confidence = min(0.6, 1.0 - distance_to_mid)
        return PivotSignal(side="buy", confidence=confidence)
    elif current_price < pivot_mid * 0.998:  # Price below mid-level
        confidence = min(0.6, 1.0 - distance_to_mid)
        return PivotSignal(side="sell", confidence=confidence)
    else:
        # Price near pivot levels - hold
        return PivotSignal(side="hold", confidence=0.3)


def compute_support_resistance_signals(df: pd.DataFrame, period: int = 20) -> PivotSignal:
    """
    Support/Resistance breakout strategy
    """
    if df.empty or len(df) < period + 1:
        return PivotSignal(side="hold", confidence=0.0)

    # Calculate support and resistance levels
    recent_data = df.tail(period)
    highs = recent_data["high"].astype(float)
    lows = recent_data["low"].astype(float)
    prices = recent_data["close"].astype(float)
    
    # Support = lowest low in period
    support = lows.min()
    # Resistance = highest high in period
    resistance = highs.max()
    
    current_price = prices.iloc[-1]
    prev_price = prices.iloc[-2] if len(prices) > 1 else current_price
    
    # Calculate confidence based on breakout strength
    breakout_strength = abs(current_price - prev_price) / prev_price
    confidence = min(breakout_strength * 10, 0.9)  # Scale confidence
    
    # Breakout signals
    if current_price > resistance * 1.001:  # Break above resistance
        return PivotSignal(side="buy", confidence=confidence)
    elif current_price < support * 0.999:  # Break below support
        return PivotSignal(side="sell", confidence=confidence)
    else:
        return PivotSignal(side="hold", confidence=0.1)


def compute_momentum_pivot_signals(df: pd.DataFrame, lookback: int = 10) -> PivotSignal:
    """
    Momentum-based pivot strategy
    """
    if df.empty or len(df) < lookback + 1:
        return PivotSignal(side="hold", confidence=0.0)

    prices = df["close"].astype(float)
    current_price = prices.iloc[-1]
    
    # Calculate momentum
    momentum = (current_price - prices.iloc[-lookback]) / prices.iloc[-lookback]
    
    # Calculate volatility
    returns = prices.pct_change().dropna()
    volatility = returns.std() if len(returns) > 0 else 0.01
    
    # Normalize momentum by volatility
    momentum_score = momentum / (volatility * np.sqrt(lookback))
    
    # Generate signals based on momentum
    if momentum_score > 0.5:  # Strong upward momentum
        confidence = min(abs(momentum_score) * 0.5, 0.8)
        return PivotSignal(side="buy", confidence=confidence)
    elif momentum_score < -0.5:  # Strong downward momentum
        confidence = min(abs(momentum_score) * 0.5, 0.8)
        return PivotSignal(side="sell", confidence=confidence)
    else:
        return PivotSignal(side="hold", confidence=0.1)
