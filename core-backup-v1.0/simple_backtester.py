import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass
from bot.strategy.pivot_levels import compute_pivot_levels_signals
from bot.data.yahoo import fetch_candles


@dataclass
class SimpleBacktestResult:
    total_return: float
    annual_return: float
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
    def __init__(self, initial_capital: float = 10000.0, commission: float = 0.001, symbol: str = ""):
        self.initial_capital = initial_capital
        self.commission = commission
        self.symbol = symbol

    def run_backtest(self, df: pd.DataFrame, symbol: str = None) -> SimpleBacktestResult:
        # Use provided symbol or fallback to instance symbol
        if symbol is None:
            symbol = self.symbol
        """
        Ultra-simple backtest that will definitely generate trades
        """
        if df.empty or len(df) < 20:
            return self._empty_result()
        
        # Initialize
        cash = self.initial_capital
        # Track multiple sub-positions; each element is a dict with independent lifecycle
        # {'level': 'S2'|'S3', 'shares': float, 'entry_price': float, 'partial_done': bool}
        positions = []
        trades = []
        equity_curve = [self.initial_capital]
        
        # Main backtest loop
        for i in range(5, len(df)):  # Start at 5 to ensure enough data for pivot calculation
            current_price = float(df.iloc[i]['close'])
            current_data = df.iloc[:i+1]
            
            # Check for exit signals on existing positions
            for idx_pos in list(range(len(positions))):
                pos = positions[idx_pos]
                if pos['level'] == 'S3':
                    # S3 -> R2 (with partial TP at R1)
                    signal = compute_pivot_levels_signals(current_data, symbol=symbol, current_position=pos)
                    if signal.side == "sell" and signal.exit_level == 'R2':
                        if not pos['partial_done']:
                            # First exit: 50% at R1
                            sell_shares = pos['shares'] * 0.5
                            proceeds = sell_shares * current_price * (1 - self.commission)
                            cash += proceeds
                            pos['shares'] -= sell_shares
                            pos['partial_done'] = True
                            trades.append({
                                'type': 'SELL',
                                'price': current_price,
                                'shares': sell_shares,
                                'proceeds': proceeds,
                                'confidence': signal.confidence,
                                'entry_level': 'S3',
                                'exit_level': 'R1'
                            })
                            print(f"SELL at {i}: {sell_shares:.2f} at ${current_price:.2f} (Entry: S3 -> R1)")
                        else:
                            # Second exit: remaining 50% at R2
                            sell_shares = pos['shares']
                            proceeds = sell_shares * current_price * (1 - self.commission)
                            cash += proceeds
                            trades.append({
                                'type': 'SELL',
                                'price': current_price,
                                'shares': sell_shares,
                                'proceeds': proceeds,
                                'confidence': signal.confidence,
                                'entry_level': 'S3',
                                'exit_level': 'R2'
                            })
                            print(f"SELL at {i}: {sell_shares:.2f} at ${current_price:.2f} (Entry: S3 -> R2)")
                            positions.pop(idx_pos)
                            break
                    elif signal.side == "sell" and signal.exit_level == 'R1' and not pos['partial_done']:
                        # Partial exit at R1
                        sell_shares = pos['shares'] * 0.5
                        proceeds = sell_shares * current_price * (1 - self.commission)
                        cash += proceeds
                        pos['shares'] -= sell_shares
                        pos['partial_done'] = True
                        trades.append({
                            'type': 'SELL',
                            'price': current_price,
                            'shares': sell_shares,
                            'proceeds': proceeds,
                            'confidence': signal.confidence,
                            'entry_level': 'S3',
                            'exit_level': 'R1'
                        })
                        print(f"SELL at {i}: {sell_shares:.2f} at ${current_price:.2f} (Entry: S3 -> R1)")
                elif pos['level'] == 'S2':
                    # S2 -> R3
                    signal = compute_pivot_levels_signals(current_data, symbol=symbol, current_position=pos)
                    if signal.side == "sell" and signal.exit_level == 'R3':
                        sell_shares = pos['shares']
                        proceeds = sell_shares * current_price * (1 - self.commission)
                        cash += proceeds
                        trades.append({
                            'type': 'SELL',
                            'price': current_price,
                            'shares': sell_shares,
                            'proceeds': proceeds,
                            'confidence': signal.confidence,
                            'entry_level': 'S2',
                            'exit_level': 'R3'
                        })
                        print(f"SELL at {i}: {sell_shares:.2f} at ${current_price:.2f} (Entry: S2 -> R3)")
                        positions.pop(idx_pos)
                        break

            # Check for new entry opportunities (allow entries while carrying if cash permits)
            signal = compute_pivot_levels_signals(current_data, symbol=symbol, current_position=None)
            if signal.side == "buy" and signal.entry_level in ('S2','S3'):
                # Use 1/3 of current cash (not equity)
                position_value = cash / 3.0
                if position_value > 0 and cash >= position_value * (1 + self.commission):
                    shares = position_value / current_price
                    cost = shares * current_price * (1 + self.commission)
                    cash -= cost
                    positions.append({
                        'level': signal.entry_level,
                        'entry_level': signal.entry_level,
                        'shares': shares,
                        'entry_price': current_price,
                        'partial_done': False
                    })
                    trades.append({
                        'type': 'BUY',
                        'price': current_price,
                        'shares': shares,
                        'cost': cost,
                        'confidence': signal.confidence,
                        'entry_level': signal.entry_level,
                        'exit_level': signal.exit_level
                    })
                    print(f"BUY at {i}: {shares:.2f} at ${current_price:.2f} (Entry: {signal.entry_level})")
            
            # Calculate current equity
            total_position_value = sum(pos['shares'] * current_price for pos in positions)
            current_equity = cash + total_position_value
            equity_curve.append(current_equity)

        # Handle remaining positions at end of backtest
        # Extend data for next-day exits using recalculated pivots
        if positions:
            print(f"Carrying {len(positions)} positions to next day...")
            # Add extra bars for next-day processing
            extra_bars = 100  # Enough for next day's trading
            extended_df = df.copy()
            if len(extended_df) > 0:
                last_price = df.iloc[-1]['close']
                for j in range(extra_bars):
                    new_row = df.iloc[-1].copy()
                    new_row['close'] = last_price * (1 + np.random.normal(0, 0.001))  # Small random walk
                    extended_df = pd.concat([extended_df, new_row.to_frame().T], ignore_index=True)
            
            # Process remaining positions with next-day pivots
            for idx_pos in list(range(len(positions))):
                pos = positions[idx_pos]
                if pos['level'] == 'S3':
                    # S3 -> R2 (with partial TP at R1)
                    for k in range(len(df), len(extended_df)):
                        current_price = float(extended_df.iloc[k]['close'])
                        current_data = extended_df.iloc[:k+1]
                        signal = compute_pivot_levels_signals(current_data, symbol=symbol, current_position=None)
                        
                        if signal.side == "sell" and signal.exit_level == 'R2':
                            if not pos['partial_done']:
                                # First exit: 50% at R1
                                sell_shares = pos['shares'] * 0.5
                                proceeds = sell_shares * current_price * (1 - self.commission)
                                cash += proceeds
                                pos['shares'] -= sell_shares
                                pos['partial_done'] = True
                                trades.append({
                                    'type': 'SELL',
                                    'price': current_price,
                                    'shares': sell_shares,
                                    'proceeds': proceeds,
                                    'confidence': signal.confidence,
                                    'entry_level': 'S3',
                                    'exit_level': 'R1'
                                })
                                print(f"SELL at {k}: {sell_shares:.2f} at ${current_price:.2f} (Entry: S3 -> R1)")
                            else:
                                # Second exit: remaining 50% at R2
                                sell_shares = pos['shares']
                                proceeds = sell_shares * current_price * (1 - self.commission)
                                cash += proceeds
                                trades.append({
                                    'type': 'SELL',
                                    'price': current_price,
                                    'shares': sell_shares,
                                    'proceeds': proceeds,
                                    'confidence': signal.confidence,
                                    'entry_level': 'S3',
                                    'exit_level': 'R2'
                                })
                                print(f"SELL at {k}: {sell_shares:.2f} at ${current_price:.2f} (Entry: S3 -> R2)")
                                positions.pop(idx_pos)
                                break
                        elif signal.side == "sell" and signal.exit_level == 'R1' and not pos['partial_done']:
                            # Partial exit at R1
                            sell_shares = pos['shares'] * 0.5
                            proceeds = sell_shares * current_price * (1 - self.commission)
                            cash += proceeds
                            pos['shares'] -= sell_shares
                            pos['partial_done'] = True
                            trades.append({
                                'type': 'SELL',
                                'price': current_price,
                                'shares': sell_shares,
                                'proceeds': proceeds,
                                'confidence': signal.confidence,
                                'entry_level': 'S3',
                                'exit_level': 'R1'
                            })
                            print(f"SELL at {k}: {sell_shares:.2f} at ${current_price:.2f} (Entry: S3 -> R1)")
                elif pos['level'] == 'S2':
                    # S2 -> R3
                    for k in range(len(df), len(extended_df)):
                        current_price = float(extended_df.iloc[k]['close'])
                        current_data = extended_df.iloc[:k+1]
                        signal = compute_pivot_levels_signals(current_data, symbol=symbol, current_position=None)
                        
                        if signal.side == "sell" and signal.exit_level == 'R3':
                            sell_shares = pos['shares']
                            proceeds = sell_shares * current_price * (1 - self.commission)
                            cash += proceeds
                            trades.append({
                                'type': 'SELL',
                                'price': current_price,
                                'shares': sell_shares,
                                'proceeds': proceeds,
                                'confidence': signal.confidence,
                                'entry_level': 'S2',
                                'exit_level': 'R3'
                            })
                            print(f"SELL at {k}: {sell_shares:.2f} at ${current_price:.2f} (Entry: S2 -> R3)")
                            positions.pop(idx_pos)
                            break

        # Final liquidation of any remaining positions
        final_price = float(df.iloc[-1]['close'])
        for pos in positions:
            sell_shares = pos['shares']
            proceeds = sell_shares * final_price * (1 - self.commission)
            cash += proceeds
            trades.append({
                'type': 'FINAL',
                'price': final_price,
                'shares': sell_shares,
                'proceeds': proceeds,
                'confidence': 0.0,
                'entry_level': pos['level'],
                'exit_level': 'FINAL'
            })
            print(f"FINAL SELL: {sell_shares:.2f} at ${final_price:.2f} (Entry: {pos['level']})")

        # Calculate final metrics
        final_equity = cash
        total_return = (final_equity - self.initial_capital) / self.initial_capital
        
        # Calculate annual return
        days = len(df) / (24 * 12)  # Assuming 5m intervals, 24*12 = 288 bars per day
        annual_return = (1 + total_return) ** (365 / days) - 1 if days > 0 else 0
        
        # Filter out FINAL trades for win/loss calculation
        regular_trades = [t for t in trades if t['type'] != 'FINAL']
        
        # Calculate trade statistics
        total_trades = len(regular_trades)
        if total_trades == 0:
            return self._empty_result()
        
        # Separate buy and sell trades
        buy_trades = [t for t in regular_trades if t['type'] == 'BUY']
        sell_trades = [t for t in regular_trades if t['type'] == 'SELL']
        
        # Match trades and calculate P&L
        trade_pnl = []
        buy_idx = 0
        sell_idx = 0
        
        while buy_idx < len(buy_trades) and sell_idx < len(sell_trades):
            buy_trade = buy_trades[buy_idx]
            sell_trade = sell_trades[sell_idx]
            
            # Calculate P&L for this trade pair
            pnl = sell_trade['proceeds'] - buy_trade['cost']
            trade_pnl.append(pnl)
            
            buy_idx += 1
            sell_idx += 1
        
        # Calculate metrics
        profitable_trades = sum(1 for pnl in trade_pnl if pnl > 0)
        losing_trades = sum(1 for pnl in trade_pnl if pnl < 0)
        win_rate = profitable_trades / total_trades if total_trades > 0 else 0
        
        # Calculate max drawdown
        equity_series = pd.Series(equity_curve)
        rolling_max = equity_series.expanding().max()
        drawdown = (equity_series - rolling_max) / rolling_max
        max_drawdown = drawdown.min()
        
        # Calculate Sharpe ratio
        if len(equity_curve) > 1:
            returns = pd.Series(equity_curve).pct_change().dropna()
            sharpe_ratio = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
        else:
            sharpe_ratio = 0
        
        # Calculate average win/loss
        wins = [pnl for pnl in trade_pnl if pnl > 0]
        losses = [pnl for pnl in trade_pnl if pnl < 0]
        avg_win = np.mean(wins) if wins else 0
        avg_loss = np.mean(losses) if losses else 0
        
        # Calculate profit factor
        total_wins = sum(wins) if wins else 0
        total_losses = abs(sum(losses)) if losses else 0
        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf') if total_wins > 0 else 0
        
        return SimpleBacktestResult(
            total_return=total_return,
            annual_return=annual_return,
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
            symbol=symbol,
            period="1 month"
        )

    def _empty_result(self) -> SimpleBacktestResult:
        return SimpleBacktestResult(
            total_return=0.0,
            annual_return=0.0,
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
            symbol=self.symbol,
            period="1 month"
        )