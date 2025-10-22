import typer
from .runner import run_loop, backfill_data
from .web_ui import app as web_app

app = typer.Typer(help="Trading bot CLI")


@app.command()
def run(
    symbol: str = typer.Option("AAPL", help="Ticker symbol"),
    interval: str = typer.Option("1h", help="Bar interval, e.g. 1m, 5m, 1h, 1d"),
    sma_fast: int = typer.Option(20, help="Fast SMA window"),
    sma_slow: int = typer.Option(50, help="Slow SMA window"),
    lookback: int = typer.Option(300, help="Bars to fetch for context"),
    position_size: int = typer.Option(1, help="Number of shares per signal"),
):
    """Run paper trading loop until stopped."""
    run_loop(symbol=symbol, interval=interval, sma_fast=sma_fast, sma_slow=sma_slow, lookback=lookback, position_size=position_size)


@app.command()
def backfill(
    symbol: str = typer.Option("AAPL", help="Ticker symbol"),
    interval: str = typer.Option("1h", help="Bar interval"),
    lookback: int = typer.Option(500, help="Bars to fetch"),
):
    """Backfill historical candles into storage."""
    backfill_data(symbol=symbol, interval=interval, lookback=lookback)


@app.command()
def web():
    """Start web dashboard."""
    web_app.run(debug=True, host='0.0.0.0', port=5000)
