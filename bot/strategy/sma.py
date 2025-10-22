import pandas as pd
from dataclasses import dataclass


@dataclass
class SMASignal:
    side: str  # 'buy', 'sell', 'hold'


def compute_sma_signals(df: pd.DataFrame, fast: int, slow: int) -> SMASignal:
    if df.empty or len(df) < max(fast, slow) + 1:
        return SMASignal(side="hold")

    prices = df["close"].astype(float)
    sma_fast = prices.rolling(window=fast).mean()
    sma_slow = prices.rolling(window=slow).mean()

    prev_fast, prev_slow = sma_fast.iloc[-2], sma_slow.iloc[-2]
    last_fast, last_slow = sma_fast.iloc[-1], sma_slow.iloc[-1]

    if pd.isna(prev_fast) or pd.isna(prev_slow) or pd.isna(last_fast) or pd.isna(last_slow):
        return SMASignal(side="hold")

    if prev_fast <= prev_slow and last_fast > last_slow:
        return SMASignal(side="buy")
    if prev_fast >= prev_slow and last_fast < last_slow:
        return SMASignal(side="sell")
    return SMASignal(side="hold")
