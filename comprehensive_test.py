"""
Kapsamlı Test: Son 1 yıl verisi + Farklı stratejiler
Bot'u kar eden hale getirmek için kapsamlı analiz
"""
import pandas as pd
from datetime import datetime
from bot.data.yahoo import fetch_candles
from bot.strategy.bot_hunter import compute_bot_hunter_signals
from bot.strategy.ema_rsi_atr import compute_ema_rsi_atr_signals
from bot.strategy.pivot_levels import compute_pivot_levels_signals
from bot.exchange.paper import PaperExchange


class ComprehensiveBacktester:
    """Kapsamlı backtester - farklı stratejileri test eder"""
    
    def __init__(self, initial_capital: float = 10000.0, commission: float = 0.001):
        self.initial_capital = initial_capital
        self.commission = commission
    
    def run_backtest(self, df: pd.DataFrame, symbol: str, strategy_name: str = "bot_hunter"):
        """Farklı stratejilerle backtest"""
        
        if df.empty or len(df) < 200:
            return self._empty_result()
        
        exchange = PaperExchange(self.initial_capital)
        trades = []
        equity_curve = [self.initial_capital]
        
        # Kripto için parametreler
        is_crypto = symbol.endswith('-USD') and symbol not in ['AAPL', 'TSLA', 'MSFT', 'GOOGL']
        
        if is_crypto:
            stop_loss = 0.03
            take_profit = 0.06
            min_confidence = 0.70
            position_size = 0.4
        else:
            stop_loss = 0.05
            take_profit = 0.10
            min_confidence = 0.4
            position_size = 0.7
        
        # Trend filtresi (kripto için)
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
            
            # Strateji seçimi
            if strategy_name == "bot_hunter":
                signal = compute_bot_hunter_signals(current_data, symbol=symbol)
            elif strategy_name == "ema_rsi_atr":
                signal = compute_ema_rsi_atr_signals(current_data)
            elif strategy_name == "pivot":
                signal = compute_pivot_levels_signals(current_data, symbol=symbol)
            else:
                signal = compute_bot_hunter_signals(current_data, symbol=symbol)
            
            current_equity = exchange.cash + (exchange.position * current_price)
            equity_curve.append(current_equity)
            
            # Stop-loss ve take-profit
            if exchange.position > 0 and exchange.avg_entry_price:
                pnl_pct = (current_price - exchange.avg_entry_price) / exchange.avg_entry_price
                
                if pnl_pct <= -stop_loss:
                    sell_qty = exchange.position
                    exchange.market_sell(symbol, sell_qty, current_price)
                    trades.append({'type': 'STOP_LOSS', 'pnl_pct': pnl_pct})
                    continue
                
                if pnl_pct >= take_profit:
                    sell_qty = exchange.position
                    exchange.market_sell(symbol, sell_qty, current_price)
                    trades.append({'type': 'TAKE_PROFIT', 'pnl_pct': pnl_pct})
                    continue
            
            # Sinyal bazlı işlemler
            if signal.side == "buy" and exchange.position <= 0:
                signal_confidence = getattr(signal, 'confidence', 0.5)
                
                if signal_confidence > min_confidence:
                    if is_crypto and not is_uptrend:
                        continue
                    
                    account_balance = exchange.cash + (exchange.position * current_price if exchange.position > 0 else 0)
                    position_value = account_balance * position_size
                    qty = position_value / current_price
                    
                    if qty > 0 and exchange.cash >= position_value * (1 + self.commission):
                        exchange.market_buy(symbol, int(qty * 10000) / 10000, current_price)
                        trades.append({'type': 'BUY'})
            
            elif signal.side == "sell" and exchange.position > 0:
                signal_confidence = getattr(signal, 'confidence', 0.5)
                
                if signal_confidence > min_confidence:
                    sell_qty = exchange.position
                    entry_price = exchange.avg_entry_price if exchange.avg_entry_price else current_price
                    exchange.market_sell(symbol, sell_qty, current_price)
                    pnl_pct = (current_price - entry_price) / entry_price
                    trades.append({'type': 'SELL', 'pnl_pct': pnl_pct})
        
        # Kalan pozisyonu kapat
        if exchange.position > 0:
            final_price = float(df.iloc[-1]['close'])
            exchange.market_sell(symbol, exchange.position, final_price)
        
        # Sonuçları hesapla
        final_equity = exchange.cash
        total_return = (final_equity - self.initial_capital) / self.initial_capital
        
        # Trade istatistikleri
        buy_trades = [t for t in trades if t['type'] == 'BUY']
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
            'max_drawdown': max_drawdown,
            'trades': trades
        }
    
    def _empty_result(self):
        return {
            'total_return': 0.0,
            'final_equity': self.initial_capital,
            'total_trades': 0,
            'win_rate': 0.0,
            'max_drawdown': 0.0,
            'trades': []
        }


def test_all_strategies():
    """Tüm stratejileri test et"""
    
    print("="*100)
    print("KAPSAMLI TEST: Son 1 Yıl + Farklı Stratejiler")
    print("="*100)
    
    symbols = ["BTC-USD", "ETH-USD"]
    strategies = ["bot_hunter", "ema_rsi_atr", "pivot"]
    intervals = ["1d"]  # Günlük interval (long-term)
    
    results = []
    
    for symbol in symbols:
        print(f"\n{'='*100}")
        print(f"TEST: {symbol}")
        print(f"{'='*100}")
        
        # Son 1 yıl verisi çek
        df = fetch_candles(symbol, "1d", 365)
        
        if df.empty or len(df) < 200:
            print(f"Yetersiz veri: {symbol}")
            continue
        
        print(f"Veri Aralığı: {df.index[0]} - {df.index[-1]}")
        print(f"Toplam Gün: {len(df)}")
        print(f"Fiyat Değişimi: {((df.iloc[-1]['close'] - df.iloc[0]['close']) / df.iloc[0]['close']):+.2%}")
        
        for strategy in strategies:
            print(f"\n  Strateji: {strategy.upper()}")
            
            backtester = ComprehensiveBacktester()
            result = backtester.run_backtest(df, symbol, strategy)
            
            print(f"    Getiri: {result['total_return']:+.2%}")
            print(f"    İşlem: {result['total_trades']}")
            print(f"    Kazanma Oranı: {result['win_rate']:.1%}")
            print(f"    Max Drawdown: {result['max_drawdown']:.2%}")
            
            results.append({
                'symbol': symbol,
                'strategy': strategy,
                'return': result['total_return'],
                'trades': result['total_trades'],
                'win_rate': result['win_rate'],
                'max_drawdown': result['max_drawdown']
            })
    
    # Özet
    print(f"\n{'='*100}")
    print("ÖZET TABLO")
    print(f"{'='*100}")
    print(f"{'Sembol':<12} {'Strateji':<20} {'Getiri':<12} {'İşlem':<8} {'Kazanma %':<12} {'Max DD':<10}")
    print("-"*100)
    
    results_sorted = sorted(results, key=lambda x: x['return'], reverse=True)
    
    for r in results_sorted:
        return_str = f"{r['return']:+.2%}"
        trades_str = f"{r['trades']}"
        win_str = f"{r['win_rate']:.1%}"
        dd_str = f"{r['max_drawdown']:.2%}"
        
        print(f"{r['symbol']:<12} {r['strategy']:<20} {return_str:<12} {trades_str:<8} {win_str:<12} {dd_str:<10}")
    
    # En iyi strateji
    if results_sorted:
        best = results_sorted[0]
        print(f"\n{'='*100}")
        print(f"EN İYİ STRATEJİ:")
        print(f"  Sembol: {best['symbol']}")
        print(f"  Strateji: {best['strategy']}")
        print(f"  Getiri: {best['return']:+.2%}")
        print(f"  İşlem: {best['trades']}")
        print(f"  Kazanma Oranı: {best['win_rate']:.1%}")
        
        # Kar eden stratejiler
        profitable = [r for r in results if r['return'] > 0]
        if profitable:
            print(f"\n{'='*100}")
            print(f"KAR EDEN STRATEJİLER ({len(profitable)}/{len(results)}):")
            for p in sorted(profitable, key=lambda x: x['return'], reverse=True):
                print(f"  {p['symbol']} - {p['strategy']}: {p['return']:+.2%}")
        else:
            print(f"\n{'='*100}")
            print("⚠️ HİÇBİR STRATEJİ KAR ETMİYOR!")
            print("Optimizasyon veya farklı yaklaşım gerekli.")


if __name__ == "__main__":
    test_all_strategies()

