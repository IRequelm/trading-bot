import pandas as pd
from typing import Dict

def calculate_camarilla_pivots(high: float, low: float, close: float, open: float = None) -> Dict[str, float]:
    """
    Calculate Camarilla Pivot Points
    Formula: PP = (H + L + C) / 3
    
    Camarilla Supports/Resistances use different formulas:
    R4 = C + (H - L) * 1.1/2
    R3 = C + (H - L) * 1.1/4
    R2 = C + (H - L) * 1.1/6
    R1 = C + (H - L) * 1.1/12
    S1 = C - (H - L) * 1.1/12
    S2 = C - (H - L) * 1.1/6
    S3 = C - (H - L) * 1.1/4
    S4 = C - (H - L) * 1.1/2
    """
    pivot = (high + low + close) / 3
    range_val = high - low
    
    # Camarilla formulas
    r4 = close + (range_val * 1.1 / 2)
    r3 = close + (range_val * 1.1 / 4)
    r2 = close + (range_val * 1.1 / 6)
    r1 = close + (range_val * 1.1 / 12)
    s1 = close - (range_val * 1.1 / 12)
    s2 = close - (range_val * 1.1 / 6)
    s3 = close - (range_val * 1.1 / 4)
    s4 = close - (range_val * 1.1 / 2)
    
    return {
        'pivot': pivot,
        's1': s1,
        's2': s2,
        's3': s3,
        's4': s4,
        'r1': r1,
        'r2': r2,
        'r3': r3,
        'r4': r4
    }


def get_daily_ohlc(df: pd.DataFrame, symbol: str = "") -> Dict[str, float]:
    """
    Get YESTERDAY's OHLC for pivot calculation (as TradingView does)
    For stocks: Use previous trading day's OHLC
    For crypto: Use last 24h OHLC
    """
    is_crypto = any(x in symbol.upper() for x in ['BTC', 'ETH', 'CRYPTO', '-USD'])
    
    if is_crypto:
        # Crypto: use last 288 bars (24h for 5m data)
        recent_data = df.tail(288)
    else:
        # Stocks: Need YESTERDAY's data
        # For BIST (ASELS), trading is 10:00-17:00
        # Get the first half of last 300 bars as "yesterday"
        recent_data = df.tail(300)
        if len(recent_data) > 200:
            # Split: first half = yesterday, second half = today
            mid_point = len(recent_data) // 2
            recent_data = recent_data.iloc[:mid_point]  # Yesterday's data
    
    if len(recent_data) < 50:
        return {}
    
    # Get OHLC from the selected period (yesterday for stocks)
    high = float(recent_data['high'].max())
    low = float(recent_data['low'].min())
    close = float(recent_data['close'].iloc[-1])
    
    return {
        'high': high,
        'low': low,
        'close': close
    }


def calculate_daily_pivot_levels(df: pd.DataFrame, symbol: str = "") -> Dict[str, float]:
    """Calculate daily pivot levels using Camarilla method"""
    ohlc = get_daily_ohlc(df, symbol)
    if not ohlc:
        return {}
    
    return calculate_camarilla_pivots(ohlc['high'], ohlc['low'], ohlc['close'])

