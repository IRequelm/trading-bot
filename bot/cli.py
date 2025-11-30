import typer
from .runner import run_loop, backfill_data
from .web_ui import app as web_app
from .data.yahoo import fetch_candles
from .backtest.simple_backtester import SimpleBacktester
import pandas as pd
from typing import List, Tuple

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


def _default_top_crypto() -> List[str]:
    return [
        "BTC-USD","ETH-USD","BNB-USD","SOL-USD","XRP-USD","USDC-USD","ADA-USD","DOGE-USD","TRX-USD","TON-USD",
        "AVAX-USD","SHIB-USD","LINK-USD","DOT-USD","BCH-USD","MATIC-USD","LTC-USD","UNI-USD","ATOM-USD","ETC-USD",
        "XLM-USD","OKB-USD","XMR-USD","APT-USD","HBAR-USD","FIL-USD","ARB-USD","IMX-USD","NEAR-USD","VET-USD",
        "INJ-USD","OP-USD","TIA-USD","RNDR-USD","AAVE-USD","ALGO-USD","SUI-USD","FLOW-USD","QNT-USD","EGLD-USD",
        "MKR-USD","RUNE-USD","GRT-USD","SAND-USD","AXS-USD","KAS-USD","FTM-USD","HBTC-USD","MAN-USD","PEPE-USD"
    ]


@app.command()
def crypto_suite(
    interval: str = typer.Option("5m", help="Bar interval, e.g. 5m"),
    lookback: int = typer.Option(3000, help="Bars to fetch per symbol (~1-2 months for 5m)"),
    initial_equity: float = typer.Option(10000.0, help="Starting equity"),
    commission: float = typer.Option(0.001, help="Commission fraction per trade"),
    list_file: str = typer.Option("crypto_top100.txt", help="Optional file with one symbol per line"),
    top_n: int = typer.Option(10, help="Show top N results"),
):
    """Run backtests over Top 100 crypto and print leaders."""
    symbols: List[str] = []
    try:
        with open(list_file, 'r', encoding='utf-8') as f:
            symbols = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    except FileNotFoundError:
        symbols = _default_top_crypto()

    results: List[Tuple[str, float, float, int, float, float]] = []
    for sym in symbols:
        try:
            df = fetch_candles(sym, interval, lookback)
            if df is None or len(df) < 200:
                continue
            bt = SimpleBacktester(initial_equity, commission, sym)
            r = bt.run_backtest(df)
            results.append((sym, r.total_return, r.final_equity, r.total_trades, r.win_rate, r.max_drawdown))
            print(f"DONE {sym}: return={r.total_return:.2%}, trades={r.total_trades}, win={r.win_rate:.1%}, eq=${r.final_equity:.2f}")
        except Exception as e:
            print(f"SKIP {sym}: {e}")

    if not results:
        print("No results generated.")
        return

    results.sort(key=lambda x: x[1], reverse=True)
    print("\nTop performers:")
    for sym, ret, eq, trades, win, dd in results[:top_n]:
        print(f"{sym}: return={ret:.2%}, equity=${eq:.2f}, trades={trades}, win={win:.1%}, maxDD={dd:.2%}")
