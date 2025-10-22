import time
import pandas as pd
from .config import settings
from .data.yahoo import fetch_candles
from .strategy.sma import compute_sma_signals
from .exchange.paper import PaperExchange
from .storage.db import Database


def run_loop(symbol: str, interval: str, sma_fast: int, sma_slow: int, lookback: int, position_size: int) -> None:
    db = Database()
    ex = PaperExchange(starting_cash=settings.paper_starting_cash)

    while True:
        df = fetch_candles(symbol=symbol, interval=interval, lookback=lookback)
        if df.empty:
            time.sleep(5)
            continue

        signal = compute_sma_signals(df, fast=sma_fast, slow=sma_slow)
        last_row = df.iloc[-1]
        price = float(last_row["close"]) if "close" in last_row else float(df["close"].iloc[-1])

        if signal.side == "buy":
            if ex.position <= 0:
                ex.market_buy(symbol, qty=position_size, price=price)
        elif signal.side == "sell":
            if ex.position >= 0 and ex.position > 0:
                ex.market_sell(symbol, qty=min(position_size, ex.position), price=price)

        db.record_equity(timestamp=int(last_row["timestamp"]), equity=ex.cash + ex.position * price)
        time.sleep(5)


def backfill_data(symbol: str, interval: str, lookback: int) -> None:
    db = Database()
    df = fetch_candles(symbol=symbol, interval=interval, lookback=lookback)
    if df.empty:
        return
    db.insert_candles(symbol=symbol, interval=interval, candles=df)

