from pydantic_settings import BaseSettings
from typing import Literal
import os
from dotenv import load_dotenv

# Load .env if present
load_dotenv(override=False)

Interval = Literal["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "1wk", "1mo"]


class Settings(BaseSettings):
    bot_env: str = os.getenv("BOT_ENV", "development")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    paper_starting_cash: float = float(os.getenv("PAPER_STARTING_CASH", "10000"))
    data_provider: str = os.getenv("DATA_PROVIDER", "yfinance")

    class Config:
        extra = "ignore"


settings = Settings()
