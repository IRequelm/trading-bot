"""
Agresif Optimizasyon - Bot'u kar eden hale getirmek için
Grid search ile en iyi parametreleri bulur
"""
import pandas as pd
import numpy as np
from datetime import datetime
from bot.data.yahoo import fetch_candles
from bot.strategy.bot_hunter import compute_bot_hunter_signals
from bot.exchange.paper import PaperExchange
from itertools import product


class OptimizedBacktester:
    """Optimize edilmiş backtester"""
    
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
            return self._empty_result()
        
        exchange = PaperExchange(self.initial_capital)
        trades = []
        equity_curve = [self.initial_capital]
        
        # Trend filtresi
        close = df['close'].astype(float)
        ema_50 = close.ewm(span=50).mean()
        ema_200 = close.ewm(span=200).mean()
        
        for i in range(200, len(df)):
            current_data = df.iloc[:i+1]
            current_price = float(current_data.iloc[-1]['close'])
            
            # Trend kontrolü
            current_ema_50 = ema_50.iloc[i] if i < len(ema_50) else current_price
            current_ema_200 = ema_200.iloc[i] if i < len(ema_200) else current_price
            is_uptrend = current_ema_50 > current_ema_200
            
            signal = compute_bot_hunter_signals(current_data, symbol=symbol)
            current_equity = exchange.cash + (exchange.position * current_price)
            equity_curve.append(current_equity)
            
            # Stop-loss ve take-profit
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
            
            # Sinyal bazlı işlemler
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
        
        # Kalan pozisyonu kapat
        if exchange.position > 0:
            final_price = float(df.iloc[-1]['close'])
            exchange.market_sell(symbol, exchange.position, final_price)
        
        final_equity = exchange.cash
        total_return = (final_equity - self.initial_capital) / self.initial_capital
        
        # Trade istatistikleri
        sell_trades = [t for t in trades if t['type'] in ['SELL', 'TAKE_PROFIT', 'STOP_LOSS']]
        trade_pnl = [t.get('pnl_pct', 0) for t in sell_trades]
        profitable = sum(1 for pnl in trade_pnl if pnl > 0)
        win_rate = profitable / len(trade_pnl) if trade_pnl else 0
        
        # Max drawdown
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
    
    def _empty_result(self):
        return {
            'total_return': 0.0,
            'final_equity': self.initial_capital,
            'total_trades': 0,
            'win_rate': 0.0,
            'max_drawdown': 0.0
        }


def optimize_parameters(symbol: str, df: pd.DataFrame):
    """Parametre optimizasyonu - Grid Search"""
    
    print(f"\n{'='*100}")
    print(f"OPTIMIZASYON: {symbol}")
    print(f"{'='*100}")
    
    # Test edilecek parametreler (daha geniş aralık)
    stop_loss_options = [0.02, 0.03, 0.04, 0.05, 0.06]  # %2-6
    take_profit_options = [0.05, 0.08, 0.10, 0.12, 0.15]  # %5-15
    confidence_options = [0.65, 0.70, 0.75, 0.80]  # %65-80
    position_size_options = [0.3, 0.4, 0.5, 0.6]  # %30-60
    trend_filter_options = [True, False]
    
    total_combinations = len(stop_loss_options) * len(take_profit_options) * len(confidence_options) * len(position_size_options) * len(trend_filter_options)
    
    print(f"Toplam kombinasyon: {total_combinations}")
    print("Optimizasyon başlıyor... (bu biraz zaman alabilir)\n")
    
    best_result = None
    best_params = None
    best_return = float('-inf')
    results = []
    
    count = 0
    
    for stop_loss, take_profit, min_conf, pos_size, use_trend in product(
        stop_loss_options, take_profit_options, confidence_options, 
        position_size_options, trend_filter_options
    ):
        count += 1
        if count % 50 == 0:
            print(f"Test {count}/{total_combinations}... (En iyi: {best_return:+.2%})")
        
        backtester = OptimizedBacktester()
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
    
    # En iyi sonuçları göster
    print(f"\n{'='*100}")
    print(f"OPTIMIZASYON SONUÇLARI: {symbol}")
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
    
    # Top 10 sonuç
    results_sorted = sorted(results, key=lambda x: x['return'], reverse=True)
    print(f"\n{'='*100}")
    print(f"TOP 10 SONUÇ:")
    print(f"{'='*100}")
    print(f"{'#':<4} {'Getiri':<12} {'SL':<8} {'TP':<8} {'Conf':<8} {'Size':<8} {'Trend':<8} {'İşlem':<8} {'Win%':<8}")
    print("-"*100)
    
    for i, r in enumerate(results_sorted[:10], 1):
        print(f"{i:<4} {r['return']:+.2%} {'':<4} {r['stop_loss']:.1%} {'':<4} {r['take_profit']:.1%} {'':<4} {r['min_confidence']:.0%} {'':<4} {r['position_size']:.0%} {'':<4} {str(r['use_trend']):<8} {'':<4} {r['trades']:<8} {r['win_rate']:.1%}")
    
    # Kar eden sonuçlar
    profitable = [r for r in results if r['return'] > 0 and r['trades'] > 0]
    print(f"\n{'='*100}")
    print(f"KAR EDEN KOMBİNASYONLAR: {len(profitable)}/{len(results)}")
    print(f"{'='*100}")
    
    if profitable:
        print(f"En iyi {min(10, len(profitable))} kar eden kombinasyon:")
        for i, p in enumerate(sorted(profitable, key=lambda x: x['return'], reverse=True)[:10], 1):
            print(f"{i}. Return: {p['return']:+.2%} | SL: {p['stop_loss']:.1%} | TP: {p['take_profit']:.1%} | "
                  f"Conf: {p['min_confidence']:.0%} | Size: {p['position_size']:.0%} | "
                  f"Trend: {p['use_trend']} | Trades: {p['trades']} | Win: {p['win_rate']:.1%}")
    else:
        print("⚠️ HİÇBİR KOMBİNASYON KAR ETMİYOR!")
        print("Farklı bir yaklaşım gerekebilir.")
    
    return best_params, best_result


def main():
    """Ana optimizasyon fonksiyonu"""
    
    print("="*100)
    print("AGRESİF OPTİMİZASYON - Bot'u Kar Eden Hale Getirmek")
    print("="*100)
    print(f"Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nBu işlem 1-2 saat sürebilir...")
    
    symbols = ["BTC-USD", "ETH-USD"]
    
    all_best_params = {}
    
    for symbol in symbols:
        print(f"\n{'='*100}")
        print(f"{symbol} OPTİMİZASYONU BAŞLIYOR...")
        print(f"{'='*100}")
        
        # Son 1 yıl verisi (günlük)
        df = fetch_candles(symbol, "1d", 365)
        
        if df.empty or len(df) < 200:
            print(f"Yetersiz veri: {symbol}")
            continue
        
        print(f"Veri Aralığı: {df.index[0]} - {df.index[-1]}")
        print(f"Toplam Gün: {len(df)}")
        
        best_params, best_result = optimize_parameters(symbol, df)
        
        if best_params:
            all_best_params[symbol] = best_params
    
    # Özet
    print(f"\n{'='*100}")
    print("GENEL ÖZET")
    print(f"{'='*100}")
    
    for symbol, params in all_best_params.items():
        print(f"\n{symbol}:")
        print(f"  Stop Loss: {params['stop_loss']:.1%}")
        print(f"  Take Profit: {params['take_profit']:.1%}")
        print(f"  Min Confidence: {params['min_confidence']:.0%}")
        print(f"  Position Size: {params['position_size']:.0%}")
        print(f"  Trend Filter: {params['use_trend']}")


if __name__ == "__main__":
    main()

