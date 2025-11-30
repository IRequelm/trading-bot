"""
Bot Hunter Stratejisi Performans Testi
Son 1 aylık verilerle test eder
"""
import sys
import os
from datetime import datetime
import pandas as pd
from bot.data.yahoo import fetch_candles
from bot.strategy.bot_hunter import compute_bot_hunter_signals
from bot.exchange.paper import PaperExchange


class BotHunterBacktester:
    def __init__(self, initial_capital: float = 10000.0, commission: float = 0.001):
        self.initial_capital = initial_capital
        self.commission = commission
        
    def run_backtest(self, df: pd.DataFrame, symbol: str = "") -> dict:
        """Bot Hunter stratejisi ile backtest"""
        if df.empty or len(df) < 50:
            return self._empty_result()
        
        exchange = PaperExchange(self.initial_capital)
        trades = []
        equity_curve = [self.initial_capital]
        
        # Sessiz mod - sadece sonuçları göster
        # print(f"\n{'='*60}")
        # print(f"Bot Hunter Backtest: {symbol}")
        # print(f"{'='*60}")
        # print(f"Başlangıç sermayesi: ${self.initial_capital:,.2f}")
        # print(f"Veri sayısı: {len(df)} bar")
        # print(f"Tarih aralığı: {df.index[0]} - {df.index[-1]}")
        
        # Backtest loop
        for i in range(50, len(df)):  # İlk 50 bar'ı gösterge hesaplamak için kullan
            current_data = df.iloc[:i+1]
            current_price = float(current_data.iloc[-1]['close'])
            
            # Bot Hunter sinyali al
            signal = compute_bot_hunter_signals(current_data, symbol=symbol)
            
            # Mevcut pozisyon kontrolü
            current_equity = exchange.cash + (exchange.position * current_price)
            equity_curve.append(current_equity)
            
            # Stop-loss ve take-profit (kripto için optimize edilmiş)
            if exchange.position > 0 and exchange.avg_entry_price:
                pnl_pct = (current_price - exchange.avg_entry_price) / exchange.avg_entry_price
                
                # Kripto için daha sıkı stop-loss ve erken take-profit
                is_crypto = symbol.endswith('-USD') and symbol not in ['AAPL', 'TSLA', 'MSFT', 'GOOGL']
                
                if is_crypto:
                    # Kripto: %3 stop-loss, %6 take-profit (daha konservatif)
                    stop_loss = 0.03
                    take_profit = 0.06
                else:
                    # Hisse senetleri: %5 stop-loss, %10 take-profit
                    stop_loss = 0.05
                    take_profit = 0.10
                
                # Stop-loss
                if pnl_pct <= -stop_loss:
                    sell_qty = exchange.position
                    exchange.market_sell(symbol, sell_qty, current_price)
                    trades.append({
                        'type': 'STOP_LOSS',
                        'price': current_price,
                        'pnl_pct': pnl_pct,
                        'equity': exchange.cash
                    })
                    continue
                
                # Take-profit
                if pnl_pct >= take_profit:
                    sell_qty = exchange.position
                    exchange.market_sell(symbol, sell_qty, current_price)
                    trades.append({
                        'type': 'TAKE_PROFIT',
                        'price': current_price,
                        'pnl_pct': pnl_pct,
                        'equity': exchange.cash
                    })
                    continue
            
            # Sinyal bazlı işlemler (kripto için daha yüksek confidence + trend filtresi)
            is_crypto = symbol.endswith('-USD') and symbol not in ['AAPL', 'TSLA', 'MSFT', 'GOOGL']
            min_confidence = 0.70 if is_crypto else 0.4  # Kripto için daha yüksek threshold
            
            # Trend filtresi (kripto için)
            if is_crypto and len(df) > 200:
                close_prices = df['close'].astype(float)
                ema_50 = close_prices.ewm(span=50).mean()
                ema_200 = close_prices.ewm(span=200).mean()
                current_ema_50 = ema_50.iloc[i] if i < len(ema_50) else current_price
                current_ema_200 = ema_200.iloc[i] if i < len(ema_200) else current_price
                is_uptrend = current_ema_50 > current_ema_200
            else:
                is_uptrend = True  # Hisse senetleri için trend filtresi yok
            
            if signal.side == "buy" and exchange.position <= 0 and signal.confidence > min_confidence:
                # Kripto için sadece uptrend'de buy yap
                if is_crypto and not is_uptrend:
                    continue  # Downtrend'de buy yapma
                # Position sizing: kripto için daha konservatif
                account_balance = exchange.cash + (exchange.position * current_price if exchange.position > 0 else 0)
                if is_crypto:
                    position_size_pct = min(0.4, signal.confidence * 0.6)  # Max %40, daha konservatif
                else:
                    position_size_pct = min(0.7, signal.confidence)  # Max %70
                position_value = account_balance * position_size_pct
                qty = position_value / current_price
                
                if qty > 0 and exchange.cash >= position_value * (1 + self.commission):
                    exchange.market_buy(symbol, int(qty * 10000) / 10000, current_price)  # 4 decimal precision
                    trades.append({
                        'type': 'BUY',
                        'price': current_price,
                        'qty': qty,
                        'confidence': signal.confidence,
                        'reason': signal.reason,
                        'bot_activity': signal.bot_activity,
                        'equity': exchange.cash + (exchange.position * current_price)
                    })
                    # Sessiz mod - işlemleri gösterme
                    # if signal.confidence > 0.75:
                    #     print(f"BUY: {qty:.4f} @ ${current_price:.2f} | {signal.reason} | Conf: {signal.confidence:.2f}")
            
            elif signal.side == "sell" and exchange.position > 0 and signal.confidence > min_confidence:
                sell_qty = exchange.position
                exchange.market_sell(symbol, sell_qty, current_price)
                pnl_pct = (current_price - exchange.avg_entry_price) / exchange.avg_entry_price if exchange.avg_entry_price else 0
                trades.append({
                    'type': 'SELL',
                    'price': current_price,
                    'qty': sell_qty,
                    'pnl_pct': pnl_pct,
                    'confidence': signal.confidence,
                    'reason': signal.reason,
                    'bot_activity': signal.bot_activity,
                    'equity': exchange.cash
                })
                # Sessiz mod - işlemleri gösterme
                # if abs(pnl_pct) > 0.02 or signal.confidence > 0.75:
                #     print(f"SELL: {sell_qty:.4f} @ ${current_price:.2f} | {signal.reason} | P&L: {pnl_pct:.2%}")
        
        # Kalan pozisyonu kapat
        if exchange.position > 0:
            final_price = float(df.iloc[-1]['close'])
            exchange.market_sell(symbol, exchange.position, final_price)
            pnl_pct = (final_price - exchange.avg_entry_price) / exchange.avg_entry_price if exchange.avg_entry_price else 0
            trades.append({
                'type': 'FINAL',
                'price': final_price,
                'qty': exchange.position,
                'pnl_pct': pnl_pct,
                'equity': exchange.cash
            })
        
        # Sonuçları hesapla
        final_equity = exchange.cash
        total_return = (final_equity - self.initial_capital) / self.initial_capital
        
        # Trade istatistikleri - düzeltilmiş P&L hesaplama
        trade_pnl = []
        trade_pnl_pct = []
        
        # Tüm trade'leri sırayla işle
        position_stack = []  # (qty, entry_price) çiftleri
        
        for trade in trades:
            if trade['type'] == 'BUY':
                qty = trade.get('qty', 0)
                price = trade.get('price', 0)
                if qty > 0 and price > 0:
                    position_stack.append({'qty': qty, 'entry_price': price})
            
            elif trade['type'] in ['SELL', 'TAKE_PROFIT', 'STOP_LOSS', 'FINAL']:
                sell_qty = trade.get('qty', 0)
                sell_price = trade.get('price', 0)
                
                if sell_qty > 0 and sell_price > 0 and position_stack:
                    # FIFO ile pozisyonları kapat
                    remaining_qty = sell_qty
                    
                    while remaining_qty > 0 and position_stack:
                        position = position_stack[0]
                        position_qty = position['qty']
                        entry_price = position['entry_price']
                        
                        if position_qty <= remaining_qty:
                            # Tüm pozisyon kapatılıyor
                            pnl = (sell_price - entry_price) * position_qty
                            pnl_pct = (sell_price - entry_price) / entry_price
                            trade_pnl.append(pnl)
                            trade_pnl_pct.append(pnl_pct)
                            remaining_qty -= position_qty
                            position_stack.pop(0)
                        else:
                            # Kısmi pozisyon kapatılıyor
                            pnl = (sell_price - entry_price) * remaining_qty
                            pnl_pct = (sell_price - entry_price) / entry_price
                            trade_pnl.append(pnl)
                            trade_pnl_pct.append(pnl_pct)
                            position['qty'] -= remaining_qty
                            remaining_qty = 0
        
        # P&L yüzdesi kullanarak hesapla
        profitable_trades = sum(1 for pnl in trade_pnl_pct if pnl > 0)
        losing_trades = sum(1 for pnl in trade_pnl_pct if pnl < 0)
        win_rate = profitable_trades / len(trade_pnl_pct) if trade_pnl_pct else 0
        
        # Max drawdown
        equity_series = pd.Series(equity_curve)
        rolling_max = equity_series.expanding().max()
        drawdown = (equity_series - rolling_max) / rolling_max
        max_drawdown = drawdown.min()
        
        # Sharpe ratio
        if len(equity_curve) > 1:
            returns = pd.Series(equity_curve).pct_change().dropna()
            sharpe_ratio = returns.mean() / returns.std() * (252 ** 0.5) if returns.std() > 0 else 0
        else:
            sharpe_ratio = 0
        
        # Average win/loss (yüzde olarak)
        wins = [pnl for pnl in trade_pnl_pct if pnl > 0]
        losses = [pnl for pnl in trade_pnl_pct if pnl < 0]
        avg_win = sum(wins) / len(wins) if wins else 0
        avg_loss = sum(losses) / len(losses) if losses else 0
        
        # Profit factor (dolar bazlı)
        wins_dollar = [pnl for pnl in trade_pnl if pnl > 0]
        losses_dollar = [pnl for pnl in trade_pnl if pnl < 0]
        total_wins = sum(wins_dollar) if wins_dollar else 0
        total_losses = abs(sum(losses_dollar)) if losses_dollar else 0
        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf') if total_wins > 0 else 0
        
        return {
            'total_return': total_return,
            'final_equity': final_equity,
            'total_trades': len(trade_pnl_pct),
            'profitable_trades': profitable_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'trades': trades,
            'equity_curve': equity_curve
        }
    
    def _empty_result(self):
        return {
            'total_return': 0.0,
            'final_equity': self.initial_capital,
            'total_trades': 0,
            'profitable_trades': 0,
            'losing_trades': 0,
            'win_rate': 0.0,
            'max_drawdown': 0.0,
            'sharpe_ratio': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'profit_factor': 0.0,
            'trades': [],
            'equity_curve': [self.initial_capital]
        }


def test_bot_hunter(symbols: list, interval: str = "1h"):
    """Birden fazla sembol için Bot Hunter testi"""
    print(f"\n{'='*80}")
    print(f"BOT HUNTER STRATEJISI PERFORMANS TESTI")
    print(f"{'='*80}")
    print(f"Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Interval: {interval}")
    print(f"Başlangıç Sermayesi: $10,000")
    
    results = []
    
    for symbol in symbols:
        print(f"Test ediliyor: {symbol}...", end=" ", flush=True)
        
        try:
            # Son 1 ay verisi (720 bar for 1h)
            lookback = 720 if interval == "1h" else 8640 if interval == "5m" else 720
            df = fetch_candles(symbol, interval, lookback)
            
            if df is None or df.empty or len(df) < 50:
                print(f"[HATA] Yetersiz veri")
                continue
            
            # Backtest çalıştır
            backtester = BotHunterBacktester(initial_capital=10000.0, commission=0.001)
            result = backtester.run_backtest(df, symbol=symbol)
            
            # Sonuçları göster
            profit = result['final_equity'] - 10000.0
            if profit > 0:
                print(f"TAMAMLANDI - Getiri: {result['total_return']:+.2%} (${profit:,.2f} kar)")
            else:
                print(f"TAMAMLANDI - Getiri: {result['total_return']:+.2%} (${abs(profit):,.2f} zarar)")
            
            results.append({
                'symbol': symbol,
                'return': result['total_return'],
                'final_equity': result['final_equity'],
                'trades': result['total_trades'],
                'win_rate': result['win_rate'],
                'profit_factor': result['profit_factor'],
                'max_drawdown': result['max_drawdown'],
                'sharpe': result['sharpe_ratio']
            })
            
        except Exception as e:
            print(f"[HATA] {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # Özet tablo
    if results:
        print(f"\n{'='*80}")
        print(f"📊 ÖZET TABLO")
        print(f"{'='*80}")
        print(f"{'Sembol':<12} {'Getiri':<12} {'Bitiş Sermayesi':<18} {'İşlem':<8} {'Kazanma %':<12} {'Profit Factor':<15} {'Max DD':<10}")
        print(f"{'─'*80}")
        
        results_sorted = sorted(results, key=lambda x: x['return'], reverse=True)
        
        for r in results_sorted:
            return_str = f"{r['return']:+.2%}"
            equity_str = f"${r['final_equity']:,.2f}"
            trades_str = f"{r['trades']}"
            win_str = f"{r['win_rate']:.1%}"
            pf_str = f"{r['profit_factor']:.2f}"
            dd_str = f"{r['max_drawdown']:.2%}"
            
            print(f"{r['symbol']:<12} {return_str:<12} {equity_str:<18} {trades_str:<8} {win_str:<12} {pf_str:<15} {dd_str:<10}")
        
        # En iyi performans
        if results_sorted:
            best = results_sorted[0]
            print(f"\n[EN IYI PERFORMANS]")
            print(f"   Sembol: {best['symbol']}")
            print(f"   Getiri: {best['return']:+.2%}")
            print(f"   Bitiş Sermayesi: ${best['final_equity']:,.2f}")
            print(f"   Toplam İşlem: {best['trades']}")
            print(f"   Kazanma Oranı: {best['win_rate']:.1%}")
            
            # Ortalama performans
            avg_return = sum(r['return'] for r in results) / len(results)
            avg_equity = sum(r['final_equity'] for r in results) / len(results)
            avg_trades = sum(r['trades'] for r in results) / len(results)
            avg_win_rate = sum(r['win_rate'] for r in results) / len(results)
            
            print(f"\n📈 ORTALAMA PERFORMANS:")
            print(f"   Ortalama Getiri: {avg_return:+.2%}")
            print(f"   Ortalama Bitiş Sermayesi: ${avg_equity:,.2f}")
            print(f"   Ortalama İşlem Sayısı: {avg_trades:.1f}")
            print(f"   Ortalama Kazanma Oranı: {avg_win_rate:.1%}")


if __name__ == "__main__":
    # Test sembolleri - önce küçük set ile test
    test_symbols = [
        "BTC-USD",
        "ETH-USD",
        "AAPL",
        "TSLA",
    ]
    
    print("Optimizasyon sonrası test başlatılıyor...")
    test_bot_hunter(test_symbols, interval="1h")
    
    print(f"\n{'='*80}")
    print("[TEST TAMAMLANDI]")
    print(f"{'='*80}")

