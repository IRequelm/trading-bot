import sqlite3
import pandas as pd
from pathlib import Path

_DB_PATH = Path("bot.sqlite")


class Database:
    def __init__(self) -> None:
        self.conn = sqlite3.connect(_DB_PATH)
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS candles (
                symbol TEXT NOT NULL,
                interval TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                PRIMARY KEY (symbol, interval, timestamp)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS equity (
                timestamp INTEGER PRIMARY KEY,
                equity REAL NOT NULL
            )
            """
        )
        self.conn.commit()

    def insert_candles(self, symbol: str, interval: str, candles: pd.DataFrame) -> None:
        if candles.empty:
            return
        rows = [
            (
                symbol,
                interval,
                int(r["timestamp"]),
                float(r["open"]),
                float(r["high"]),
                float(r["low"]),
                float(r["close"]),
                float(r["volume"]),
            )
            for _, r in candles.iterrows()
        ]
        cur = self.conn.cursor()
        cur.executemany(
            """
            INSERT OR REPLACE INTO candles (symbol, interval, timestamp, open, high, low, close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        self.conn.commit()

    def record_equity(self, timestamp: int, equity: float) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT OR REPLACE INTO equity (timestamp, equity)
            VALUES (?, ?)
            """,
            (timestamp, float(equity)),
        )
        self.conn.commit()

