"""
Hızlı Optimizasyon - Daha az kombinasyon, daha hızlı sonuç
İlerleme gösterimi ile
"""
import pandas as pd
from datetime import datetime
from bot.data.yahoo import fetch_candles
from bot.strategy.bot_hunter import compute_bot_hunter_signals
from bot.exchange.paper import PaperExchange
from itertools import product


class QuickOptimizedBacktester:
    """Hızlı optimize edilmiş backtester"""
    
    def __init__(self, initial_capital: float = 10000.0, commission: float = 0.001):
        self.initial_capital = initial_capital
        self.commission = commission
    
    def run_backtest(self, df: pd.DataFrame, symbol: str, 
                    stop_loss_pct: float,
                    take_profit_pct: float,
                    min_confidence: float,
                    position_size_pct: float,
                    use_trend_filter: bool) -> dict:
        """Backtest with specific parameters"""
        
        if df.empty or len(df) < 200:
            return {'total_return': 0.0, 'final_equity': self.initial_capital, 'total_trades': 0, 'win_rate': 0.0, 'max_drawdown': 0.0}
        
        exchange = PaperExchange(self.initial_capital)
        trades = []
        equity_curve = [self.initial_capital]
        
        close = df['close'].astype(float)
        ema_50 = close.ewm(span=50).mean()
        ema_200 = close.ewm(span=200).mean()
        
        for i in range(200, len(df)):
            current_data = df.iloc[:i+1]
            current_price = float(current_data.iloc[-1]['close'])
            
            current_ema_50 = ema_50.iloc[i] if i < len(ema_50) else current_price
            current_ema_200 = ema_200.iloc[i] if i < len(ema_200) else current_price
            is_uptrend = current_ema_50 > current_ema_200
            
            signal = compute_bot_hunter_signals(current_data, symbol=symbol)
            current_equity = exchange.cash + (exchange.position * current_price)
            equity_curve.append(current_equity)
            
            if exchange.position > 0 and exchange.avg_entry_price:
                pnl_pct = (current_price - exchange.avg_entry_price) / exchange.avg_entry_price
                
                if pnl_pct <= -stop_loss_pct:
                    exchange.market_sell(symbol, exchange.position, current_price)
                    trades.append({'type': 'STOP_LOSS', 'pnl_pct': pnl_pct})
                    continue
                
                if pnl_pct >= take_profit_pct:
                    exchange.market_sell(symbol, exchange.position, current_price)
                    trades.append({'type': 'TAKE_PROFIT', 'pnl_pct': pnl_pct})
                    continue
            
            if signal.side == "buy" and exchange.position <= 0:
                if signal.confidence > min_confidence:
                    if use_trend_filter and not is_uptrend:
                        continue
                    
                    account_balance = exchange.cash + (exchange.position * current_price if exchange.position > 0 else 0)
                    position_value = account_balance * position_size_pct
                    qty = position_value / current_price
                    
                    if qty > 0 and exchange.cash >= position_value * (1 + self.commission):
                        exchange.market_buy(symbol, int(qty * 10000) / 10000, current_price)
                        trades.append({'type': 'BUY'})
            
            elif signal.side == "sell" and exchange.position > 0:
                if signal.confidence > min_confidence:
                    sell_qty = exchange.position
                    entry_price = exchange.avg_entry_price if exchange.avg_entry_price else current_price
                    exchange.market_sell(symbol, sell_qty, current_price)
                    pnl_pct = (current_price - entry_price) / entry_price
                    trades.append({'type': 'SELL', 'pnl_pct': pnl_pct})
        
        if exchange.position > 0:
            final_price = float(df.iloc[-1]['close'])
            exchange.market_sell(symbol, exchange.position, final_price)
        
        final_equity = exchange.cash
        total_return = (final_equity - self.initial_capital) / self.initial_capital
        
        sell_trades = [t for t in trades if t['type'] in ['SELL', 'TAKE_PROFIT', 'STOP_LOSS']]
        trade_pnl = [t.get('pnl_pct', 0) for t in sell_trades]
        profitable = sum(1 for pnl in trade_pnl if pnl > 0)
        win_rate = profitable / len(trade_pnl) if trade_pnl else 0
        
        equity_series = pd.Series(equity_curve)
        rolling_max = equity_series.expanding().max()
        drawdown = (equity_series - rolling_max) / rolling_max
        max_drawdown = drawdown.min()
        
        return {
            'total_return': total_return,
            'final_equity': final_equity,
            'total_trades': len(trade_pnl),
            'win_rate': win_rate,
            'max_drawdown': max_drawdown
        }


def quick_optimize(symbol: str):
    """Hızlı optimizasyon - Daha az kombinasyon"""
    
    print(f"\n{'='*100}")
    print(f"HIZLI OPTIMIZASYON: {symbol}")
    print(f"{'='*100}")
    
    df = fetch_candles(symbol, "1d", 365)
    
    if df.empty or len(df) < 200:
        print(f"Yetersiz veri: {symbol}")
        return None
    
    print(f"Veri Aralığı: {df.index[0]} - {df.index[-1]}")
    print(f"Toplam Gün: {len(df)}")
    
    # Daha az kombinasyon (hızlı test)
    stop_loss_options = [0.02, 0.03, 0.04, 0.05]  # 4 seçenek
    take_profit_options = [0.06, 0.08, 0.10, 0.12]  # 4 seçenek
    confidence_options = [0.70, 0.75, 0.80]  # 3 seçenek
    position_size_options = [0.4, 0.5, 0.6]  # 3 seçenek
    trend_filter_options = [True, False]  # 2 seçenek
    
    total_combinations = len(stop_loss_options) * len(take_profit_options) * len(confidence_options) * len(position_size_options) * len(trend_filter_options)
    
    print(f"\nToplam kombinasyon: {total_combinations}")
    print("Optimizasyon başlıyor...\n")
    
    best_result = None
    best_params = None
    best_return = float('-inf')
    results = []
    
    count = 0
    start_time = datetime.now()
    profitable_count = 0
    
    for stop_loss, take_profit, min_conf, pos_size, use_trend in product(
        stop_loss_options, take_profit_options, confidence_options, 
        position_size_options, trend_filter_options
    ):
        count += 1
        
        # Her 5 testte bir ilerleme göster
        if count % 5 == 0 or count == 1:
            elapsed = (datetime.now() - start_time).total_seconds()
            if count > 1:
                avg_time = elapsed / count
                remaining = avg_time * (total_combinations - count)
                progress = (count / total_combinations) * 100
                
                print(f"[{progress:5.1f}%] {count:3d}/{total_combinations} | "
                      f"Geçen: {elapsed/60:5.1f}dk | "
                      f"Kalan: {remaining/60:5.1f}dk | "
                      f"En iyi: {best_return:+.2%} | "
                      f"Kar eden: {profitable_count}/{len(results)}", flush=True)
            else:
                print(f"[{0:5.1f}%] {count:3d}/{total_combinations} başlatılıyor...", flush=True)
        
        backtester = QuickOptimizedBacktester()
        result = backtester.run_backtest(
            df, symbol,
            stop_loss_pct=stop_loss,
            take_profit_pct=take_profit,
            min_confidence=min_conf,
            position_size_pct=pos_size,
            use_trend_filter=use_trend
        )
        
        results.append({
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'min_confidence': min_conf,
            'position_size': pos_size,
            'use_trend': use_trend,
            'return': result['total_return'],
            'trades': result['total_trades'],
            'win_rate': result['win_rate'],
            'max_drawdown': result['max_drawdown']
        })
        
        if result['total_return'] > 0:
            profitable_count += 1
        
        if result['total_return'] > best_return and result['total_trades'] > 0:
            best_return = result['total_return']
            best_result = result
            best_params = {
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'min_confidence': min_conf,
                'position_size': pos_size,
                'use_trend': use_trend
            }
            # Yeni en iyi bulunduğunda göster
            print(f"\n  ⭐ YENİ EN İYİ! Getiri: {best_return:+.2%} | "
                  f"SL: {stop_loss:.1%} TP: {take_profit:.1%} Conf: {min_conf:.0%} "
                  f"Size: {pos_size:.0%} Trend: {use_trend} | "
                  f"İşlem: {result['total_trades']} Win: {result['win_rate']:.1%}", flush=True)
    
    total_time = (datetime.now() - start_time).total_seconds()
    print(f"\n{'='*100}")
    print(f"OPTIMIZASYON TAMAMLANDI!")
    print(f"Toplam Süre: {total_time/60:.1f} dakika")
    print(f"Ortalama: {total_time/count:.2f} saniye/test")
    print(f"{'='*100}")
    
    if best_params:
        print(f"\nEN İYİ PARAMETRELER:")
        print(f"  Stop Loss: {best_params['stop_loss']:.1%}")
        print(f"  Take Profit: {best_params['take_profit']:.1%}")
        print(f"  Min Confidence: {best_params['min_confidence']:.0%}")
        print(f"  Position Size: {best_params['position_size']:.0%}")
        print(f"  Trend Filter: {best_params['use_trend']}")
        print(f"\nSonuçlar:")
        print(f"  Getiri: {best_result['total_return']:+.2%}")
        print(f"  Final Equity: ${best_result['final_equity']:,.2f}")
        print(f"  Toplam İşlem: {best_result['total_trades']}")
        print(f"  Kazanma Oranı: {best_result['win_rate']:.1%}")
        print(f"  Max Drawdown: {best_result['max_drawdown']:.2%}")
    
    # Top 5
    results_sorted = sorted(results, key=lambda x: x['return'], reverse=True)
    print(f"\nTOP 5 SONUÇ:")
    for i, r in enumerate(results_sorted[:5], 1):
        print(f"{i}. {r['return']:+.2%} | SL: {r['stop_loss']:.1%} TP: {r['take_profit']:.1%} "
              f"Conf: {r['min_confidence']:.0%} Size: {r['position_size']:.0%} "
              f"Trend: {r['use_trend']} | İşlem: {r['trades']} Win: {r['win_rate']:.1%}")
    
    profitable = [r for r in results if r['return'] > 0 and r['trades'] > 0]
    print(f"\nKAR EDEN: {len(profitable)}/{len(results)}")
    
    return best_params, best_result


if __name__ == "__main__":
    print("="*100)
    print("HIZLI OPTIMIZASYON - İlerleme Göstergeli")
    print("="*100)
    
    symbols = ["BTC-USD", "ETH-USD"]
    
    for symbol in symbols:
        quick_optimize(symbol)
        print("\n")

