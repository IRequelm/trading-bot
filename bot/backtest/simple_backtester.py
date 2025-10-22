import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class SimpleBacktestResult:
    total_return: float
    final_equity: float
    total_trades: int
    profitable_trades: int
    losing_trades: int
    win_rate: float
    max_drawdown: float
    sharpe_ratio: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    symbol: str
    period: str


class SimpleBacktester:
    def __init__(self, initial_capital: float = 10000.0, commission: float = 0.001):
        self.initial_capital = initial_capital
        self.commission = commission

    def run_backtest(self, df: pd.DataFrame) -> SimpleBacktestResult:
        """
        Ultra-simple backtest that will definitely generate trades
        """
        if df.empty or len(df) < 20:
            return self._empty_result()
        
        # Initialize
        cash = self.initial_capital
        position = 0.0
        trades = []
        equity_curve = [self.initial_capital]
        
        print(f"Starting backtest with {len(df)} bars")
        
        # Simple strategy: buy every 10 bars, sell every 15 bars
        for i in range(20, len(df)):
            try:
                current_price = float(df.iloc[i]["close"])
                
                # Simple alternating strategy
                if i % 20 == 0 and position == 0:  # Buy every 20 bars if no position
                    # Buy with 50% of cash
                    buy_amount = cash * 0.5
                    shares = buy_amount / current_price
                    cost = shares * current_price * (1 + self.commission)
                    
                    if cash >= cost:
                        cash -= cost
                        position = shares
                        trades.append({
                            'type': 'BUY',
                            'price': current_price,
                            'shares': shares,
                            'cost': cost
                        })
                        print(f"BUY at {i}: {shares:.2f} shares at ${current_price:.2f}")
                
                elif i % 30 == 0 and position > 0:  # Sell every 30 bars if have position
                    # Sell all shares
                    proceeds = position * current_price * (1 - self.commission)
                    cash += proceeds
                    
                    trades.append({
                        'type': 'SELL',
                        'price': current_price,
                        'shares': position,
                        'proceeds': proceeds
                    })
                    print(f"SELL at {i}: {position:.2f} shares at ${current_price:.2f}")
                    position = 0
                
                # Calculate current equity
                current_equity = cash + (position * current_price)
                equity_curve.append(current_equity)
                
            except Exception as e:
                print(f"Error at index {i}: {e}")
                continue
        
        # Close any remaining position
        if position > 0:
            final_price = float(df.iloc[-1]["close"])
            proceeds = position * final_price * (1 - self.commission)
            cash += proceeds
            trades.append({
                'type': 'SELL',
                'price': final_price,
                'shares': position,
                'proceeds': proceeds
            })
            print(f"FINAL SELL: {position:.2f} shares at ${final_price:.2f}")
            position = 0
        
        final_equity = cash
        total_return = (final_equity - self.initial_capital) / self.initial_capital
        
        # Calculate metrics
        total_trades = len([t for t in trades if t['type'] == 'SELL'])
        profitable_trades = 0
        losing_trades = 0
        total_profit = 0
        total_loss = 0
        
        # Calculate trade returns
        buy_trades = [t for t in trades if t['type'] == 'BUY']
        sell_trades = [t for t in trades if t['type'] == 'SELL']
        
        for i in range(min(len(buy_trades), len(sell_trades))):
            buy_trade = buy_trades[i]
            sell_trade = sell_trades[i]
            
            if sell_trade['price'] > buy_trade['price']:
                profitable_trades += 1
                profit = (sell_trade['price'] - buy_trade['price']) * buy_trade['shares']
                total_profit += profit
            else:
                losing_trades += 1
                loss = (buy_trade['price'] - sell_trade['price']) * buy_trade['shares']
                total_loss += loss
        
        win_rate = profitable_trades / total_trades if total_trades > 0 else 0
        avg_win = total_profit / profitable_trades if profitable_trades > 0 else 0
        avg_loss = total_loss / losing_trades if losing_trades > 0 else 0
        profit_factor = total_profit / total_loss if total_loss > 0 else 0
        
        # Calculate max drawdown
        equity_series = pd.Series(equity_curve)
        peak = equity_series.expanding(min_periods=1).max()
        drawdown = (equity_series - peak) / peak
        max_drawdown = drawdown.min()
        
        # Calculate Sharpe ratio (simplified)
        returns = equity_series.pct_change().dropna()
        sharpe_ratio = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
        
        print(f"Backtest complete: {total_trades} trades, {total_return:.2%} return")
        
        return SimpleBacktestResult(
            total_return=total_return,
            final_equity=final_equity,
            total_trades=total_trades,
            profitable_trades=profitable_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            symbol="BTC-USD",
            period=f"0 to {len(df)-1}"
        )
    
    def _empty_result(self):
        return SimpleBacktestResult(
            total_return=0.0,
            final_equity=self.initial_capital,
            total_trades=0,
            profitable_trades=0,
            losing_trades=0,
            win_rate=0.0,
            max_drawdown=0.0,
            sharpe_ratio=0.0,
            avg_win=0.0,
            avg_loss=0.0,
            profit_factor=0.0,
            symbol="BTC-USD",
            period="0 to 0"
        )
