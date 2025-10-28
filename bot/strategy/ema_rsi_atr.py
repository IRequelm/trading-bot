import pandas as pd
import numpy as np
from dataclasses import dataclass


@dataclass
class EMARSignal:
    side: str  # 'buy', 'sell', 'hold'
    rsi: float
    atr: float
    confidence: float  # 0-1 confidence level


def compute_ema_rsi_atr_signals(df: pd.DataFrame, fast_ema: int = 12, slow_ema: int = 26, 
                                rsi_period: int = 14, atr_period: int = 14) -> EMARSignal:
    """
    Advanced strategy combining:
    - EMA crossover (faster than SMA)
    - RSI filter (avoid overbought/oversold)
    - ATR for dynamic stop-loss
    """
    if df.empty or len(df) < max(fast_ema, slow_ema, rsi_period, atr_period) + 1:
        return EMARSignal(side="hold", rsi=50.0, atr=0.0, confidence=0.0)

    # Calculate EMAs (more responsive than SMAs)
    prices = df["close"].astype(float)
    ema_fast = prices.ewm(span=fast_ema).mean()
    ema_slow = prices.ewm(span=slow_ema).mean()
    
    # Calculate RSI
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    # Calculate ATR (Average True Range)
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    close = prices
    
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = true_range.rolling(window=atr_period).mean()
    
    # Get current values
    current_ema_fast = ema_fast.iloc[-1]
    current_ema_slow = ema_slow.iloc[-1]
    prev_ema_fast = ema_fast.iloc[-2]
    prev_ema_slow = ema_slow.iloc[-2]
    current_rsi = rsi.iloc[-1]
    current_atr = atr.iloc[-1]
    
    # Check for NaN values
    if pd.isna(current_ema_fast) or pd.isna(current_ema_slow) or pd.isna(current_rsi) or pd.isna(current_atr):
        return EMARSignal(side="hold", rsi=50.0, atr=0.0, confidence=0.0)
    
    # EMA trend logic (not just crossover, but trend direction)
    ema_bullish = current_ema_fast > current_ema_slow  # Fast above slow = bullish trend
    ema_bearish = current_ema_fast < current_ema_slow  # Fast below slow = bearish trend
    ema_bullish_cross = prev_ema_fast <= prev_ema_slow and current_ema_fast > current_ema_slow
    ema_bearish_cross = prev_ema_fast >= prev_ema_slow and current_ema_fast < current_ema_slow
    
    # RSI conditions (very lenient for more trades)
    rsi_not_overbought = current_rsi < 85  # Not extremely overbought
    rsi_not_oversold = current_rsi > 15    # Not extremely oversold
    rsi_bullish = current_rsi > 40 and current_rsi < 80
    rsi_bearish = current_rsi < 60 and current_rsi > 20
    
    # Calculate confidence based on RSI position and EMA strength
    ema_strength = abs(current_ema_fast - current_ema_slow) / current_ema_slow
    rsi_confidence = 1 - abs(current_rsi - 50) / 50  # Higher confidence when RSI is closer to 50
    confidence = min(ema_strength * 10, rsi_confidence)  # Combine both factors
    
    # Generate signals with trend-following logic
    # Boost confidence on crossover events
    if ema_bullish_cross:
        confidence = min(confidence * 2, 1.0)  # Double confidence on crossover
    elif ema_bearish_cross:
        confidence = min(confidence * 2, 1.0)
    
    # Generate signals based on trend direction (not just crossovers)
    if ema_bullish and rsi_not_overbought:
        # Boost confidence if conditions align perfectly
        if rsi_bullish or ema_bullish_cross:
            confidence = max(confidence, 0.6)
        return EMARSignal(side="buy", rsi=current_rsi, atr=current_atr, confidence=confidence)
    elif ema_bearish and rsi_not_oversold:
        # Boost confidence if conditions align perfectly
        if rsi_bearish or ema_bearish_cross:
            confidence = max(confidence, 0.6)
        return EMARSignal(side="sell", rsi=current_rsi, atr=current_atr, confidence=confidence)
    else:
        return EMARSignal(side="hold", rsi=current_rsi, atr=current_atr, confidence=confidence)


def calculate_dynamic_stop_loss(entry_price: float, atr: float, side: str, atr_multiplier: float = 2.0) -> float:
    """
    Calculate dynamic stop-loss based on ATR
    """
    if side == "buy":
        return entry_price - (atr * atr_multiplier)
    else:  # sell
        return entry_price + (atr * atr_multiplier)


def calculate_position_size(account_balance: float, risk_per_trade: float, entry_price: float, 
                          stop_loss: float) -> float:
    """
    Calculate position size based on risk management
    """
    risk_amount = account_balance * risk_per_trade
    price_risk = abs(entry_price - stop_loss)
    
    if price_risk == 0:
        return 0
    
    position_size = risk_amount / price_risk
    return min(position_size, account_balance / entry_price)  # Don't risk more than account
