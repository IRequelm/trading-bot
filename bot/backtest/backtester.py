import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass
from ..strategy.simple_signals import compute_simple_signals, compute_alternating_signals


@dataclass
class BacktestResult:
    total_return: float
    annual_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    total_trades: int
    profitable_trades: int
    losing_trades: int
    avg_win: float
    avg_loss: float
    profit_factor: float
    equity_curve: List[float]
    trades: List[Dict]


class Backtester:
    def __init__(self, initial_capital: float = 10000, commission: float = 0.001):
        self.initial_capital = initial_capital
        self.commission = commission  # 0.1% commission per trade
        
    def run_backtest(self, df: pd.DataFrame, strategy_params: Dict = None) -> BacktestResult:
        """
        Run backtest on historical data
        """
        if strategy_params is None:
            strategy_params = {
                'fast_ema': 12,
                'slow_ema': 26,
                'rsi_period': 14,
                'atr_period': 14,
                'min_confidence': 0.1,
                'risk_per_trade': 0.02
            }
        
        # Initialize tracking variables
        cash = self.initial_capital
        position = 0
        avg_entry_price = 0
        equity_curve = [self.initial_capital]
        trades = []
        
        # Track performance metrics
        trade_returns = []
        peak_equity = self.initial_capital
        max_dd = 0
        
        print(f"Starting backtest with ${self.initial_capital:,.2f} initial capital")
        print(f"Data period: {df.index[0]} to {df.index[-1]}")
        print(f"Total bars: {len(df)}")
        
        for i in range(50, len(df)):  # Start from index 50 to ensure enough data
            try:
                # Get current price and historical data for signal calculation
                current_price = float(df.iloc[i]["close"].iloc[0])
                signal_data = df.iloc[:i+1].copy()
                
                # Calculate signal using ultra-simple strategy
                signal = compute_simple_signals(signal_data)
                
                # If no signal, try alternating strategy
                if signal.side == "hold":
                    signal = compute_alternating_signals(signal_data)
                
                # Remove confidence threshold for now - let all signals through
                # if hasattr(signal, 'confidence') and signal.confidence < strategy_params['min_confidence']:
                #     signal.side = "hold"
                
                # Debug: Print signal info
                if i % 20 == 0:  # Print every 20 iterations
                    print(f"Index {i}: Signal={signal.side}, Confidence={signal.confidence:.3f}, Price=${current_price:.2f}")
                
                # Print all non-hold signals
                if signal.side != "hold":
                    print(f"TRADE SIGNAL at {i}: {signal.side.upper()} at ${current_price:.2f} (Conf: {signal.confidence:.3f})")
                
                # Calculate current equity
                current_equity = cash + (position * current_price)
                equity_curve.append(current_equity)
                
                # Update peak and drawdown
                if current_equity > peak_equity:
                    peak_equity = current_equity
                current_dd = (peak_equity - current_equity) / peak_equity
                max_dd = max(max_dd, current_dd)
                
                # Execute trades based on signal
                if signal.side == "buy" and position <= 0:
                    # Simple position sizing - use 50% of available cash for more trades
                    available_cash = cash * 0.5
                    position_size = available_cash / current_price
                    
                    if position_size > 0 and cash >= position_size * current_price:
                        # Execute buy
                        cost = position_size * current_price * (1 + self.commission)
                        cash -= cost
                        position += position_size
                        avg_entry_price = current_price
                        
                        trades.append({
                            'type': 'BUY',
                            'date': df.index[i],
                            'price': current_price,
                            'quantity': position_size,
                            'value': cost,
                            'confidence': signal.confidence
                        })
                        
                        print(f"BUY: {position_size:.2f} shares at ${current_price:.2f} (Conf: {signal.confidence:.2f})")
                
                elif signal.side == "sell" and position > 0:
                    # Execute sell
                    sell_quantity = position  # Sell all
                    proceeds = sell_quantity * current_price * (1 - self.commission)
                    cash += proceeds
                    
                    # Calculate trade return
                    if avg_entry_price > 0:
                        trade_return = (current_price - avg_entry_price) / avg_entry_price
                        trade_returns.append(trade_return)
                        
                        if trade_return > 0:
                            print(f"SELL: {sell_quantity:.2f} shares at ${current_price:.2f} (Return: {trade_return:.2%})")
                        else:
                            print(f"SELL: {sell_quantity:.2f} shares at ${current_price:.2f} (Loss: {trade_return:.2%})")
                    
                    trades.append({
                        'type': 'SELL',
                        'date': df.index[i],
                        'price': current_price,
                        'quantity': sell_quantity,
                        'value': proceeds,
                        'return': trade_return if avg_entry_price > 0 else 0
                    })
                    
                    position -= sell_quantity
                    if position <= 0:
                        avg_entry_price = 0
                
                # Simple risk management: 10% stop-loss, 20% take-profit
                if position > 0 and avg_entry_price > 0:
                    pnl_pct = (current_price - avg_entry_price) / avg_entry_price
                    
                    if pnl_pct <= -0.10:  # 10% stop-loss
                        proceeds = position * current_price * (1 - self.commission)
                        cash += proceeds
                        trade_returns.append(pnl_pct)
                        
                        trades.append({
                            'type': 'STOP_LOSS',
                            'date': df.index[i],
                            'price': current_price,
                            'quantity': position,
                            'value': proceeds,
                            'return': pnl_pct
                        })
                        
                        print(f"STOP-LOSS: Sold {position:.2f} shares at ${current_price:.2f} (Loss: {pnl_pct:.2%})")
                        position = 0
                        avg_entry_price = 0
                        
                    elif pnl_pct >= 0.20:  # 20% take-profit
                        proceeds = position * current_price * (1 - self.commission)
                        cash += proceeds
                        trade_returns.append(pnl_pct)
                        
                        trades.append({
                            'type': 'TAKE_PROFIT',
                            'date': df.index[i],
                            'price': current_price,
                            'quantity': position,
                            'value': proceeds,
                            'return': pnl_pct
                        })
                        
                        print(f"TAKE-PROFIT: Sold {position:.2f} shares at ${current_price:.2f} (Gain: {pnl_pct:.2%})")
                        position = 0
                        avg_entry_price = 0
                            
            except Exception as e:
                print(f"Error at index {i}: {e}")
                continue
        
        # Close any remaining position
        if position > 0:
            final_price = float(df.iloc[-1]["close"])
            proceeds = position * final_price * (1 - self.commission)
            cash += proceeds
            if avg_entry_price > 0:
                trade_return = (final_price - avg_entry_price) / avg_entry_price
                trade_returns.append(trade_return)
        
        # Calculate final metrics
        final_equity = cash
        total_return = (final_equity - self.initial_capital) / self.initial_capital
        
        # Calculate annual return (assuming daily data)
        days = len(df)
        years = days / 365
        annual_return = (final_equity / self.initial_capital) ** (1 / years) - 1 if years > 0 else 0
        
        # Calculate Sharpe ratio
        if trade_returns:
            returns_std = np.std(trade_returns)
            sharpe_ratio = np.mean(trade_returns) / returns_std * np.sqrt(252) if returns_std > 0 else 0
        else:
            sharpe_ratio = 0
        
        # Calculate win rate
        winning_trades = [r for r in trade_returns if r > 0]
        losing_trades = [r for r in trade_returns if r < 0]
        win_rate = len(winning_trades) / len(trade_returns) if trade_returns else 0
        
        # Calculate profit factor
        total_wins = sum(winning_trades) if winning_trades else 0
        total_losses = abs(sum(losing_trades)) if losing_trades else 0
        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf') if total_wins > 0 else 0
        
        # Calculate average win/loss
        avg_win = np.mean(winning_trades) if winning_trades else 0
        avg_loss = np.mean(losing_trades) if losing_trades else 0
        
        print(f"\n=== BACKTEST RESULTS ===")
        print(f"Initial Capital: ${self.initial_capital:,.2f}")
        print(f"Final Equity: ${final_equity:,.2f}")
        print(f"Total Return: {total_return:.2%}")
        print(f"Annual Return: {annual_return:.2%}")
        print(f"Sharpe Ratio: {sharpe_ratio:.2f}")
        print(f"Max Drawdown: {max_dd:.2%}")
        print(f"Total Trades: {len(trade_returns)}")
        print(f"Win Rate: {win_rate:.2%}")
        print(f"Profit Factor: {profit_factor:.2f}")
        print(f"Average Win: {avg_win:.2%}")
        print(f"Average Loss: {avg_loss:.2%}")
        
        return BacktestResult(
            total_return=total_return,
            annual_return=annual_return,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_dd,
            win_rate=win_rate,
            total_trades=len(trade_returns),
            profitable_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            equity_curve=equity_curve,
            trades=trades
        )
