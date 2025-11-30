"""
Day-Trading vs Long-Term Strategy Karşılaştırması
Grafiklerden görünen pivot seviyelerini kullanarak test eder
"""
import pandas as pd
from datetime import datetime
from bot.data.yahoo import fetch_candles
from bot.strategy.bot_hunter import compute_bot_hunter_signals
from bot.exchange.paper import PaperExchange


class DayTradingBacktester:
    """Day-trading stratejisi - Günlük işlemler"""
    
    def __init__(self, initial_capital: float = 10000.0, commission: float = 0.001):
        self.initial_capital = initial_capital
        self.commission = commission
    
    def run_backtest(self, df: pd.DataFrame, symbol: str):
        """Day-trading: Günlük işlemler, sıkı stop-loss"""
        
        exchange = PaperExchange(self.initial_capital)
        trades = []
        equity_curve = [self.initial_capital]
        
        # Day-trading parametreleri
        stop_loss = 0.02  # %2 stop-loss (sıkı)
        take_profit = 0.04  # %4 take-profit (hızlı kar)
        min_confidence = 0.65
        position_size = 0.5  # %50 position size
        
        for i in range(200, len(df)):
            current_data = df.iloc[:i+1]
            current_price = float(current_data.iloc[-1]['close'])
            current_time = df.index[i]
            
            signal = compute_bot_hunter_signals(current_data, symbol=symbol)
            current_equity = exchange.cash + (exchange.position * current_price)
            equity_curve.append(current_equity)
            
            # Stop-loss ve take-profit (sıkı)
            if exchange.position > 0 and exchange.avg_entry_price:
                pnl_pct = (current_price - exchange.avg_entry_price) / exchange.avg_entry_price
                
                if pnl_pct <= -stop_loss:
                    sell_qty = exchange.position
                    entry_price = exchange.avg_entry_price
                    exchange.market_sell(symbol, sell_qty, current_price)
                    trades.append({
                        'timestamp': current_time,
                        'type': 'STOP_LOSS',
                        'price': current_price,
                        'entry_price': entry_price,
                        'quantity': sell_qty,
                        'pnl_pct': pnl_pct,
                        'pnl_usd': (current_price - entry_price) * sell_qty
                    })
                    continue
                
                if pnl_pct >= take_profit:
                    sell_qty = exchange.position
                    entry_price = exchange.avg_entry_price
                    exchange.market_sell(symbol, sell_qty, current_price)
                    trades.append({
                        'timestamp': current_time,
                        'type': 'TAKE_PROFIT',
                        'price': current_price,
                        'entry_price': entry_price,
                        'quantity': sell_qty,
                        'pnl_pct': pnl_pct,
                        'pnl_usd': (current_price - entry_price) * sell_qty
                    })
                    continue
            
            # Sinyal bazlı işlemler
            if signal.side == "buy" and exchange.position <= 0 and signal.confidence > min_confidence:
                account_balance = exchange.cash + (exchange.position * current_price if exchange.position > 0 else 0)
                position_value = account_balance * position_size
                qty = position_value / current_price
                
                if qty > 0 and exchange.cash >= position_value * (1 + self.commission):
                    exchange.market_buy(symbol, int(qty * 10000) / 10000, current_price)
                    trades.append({
                        'timestamp': current_time,
                        'type': 'BUY',
                        'price': current_price,
                        'quantity': qty,
                        'confidence': signal.confidence
                    })
            
            elif signal.side == "sell" and exchange.position > 0 and signal.confidence > min_confidence:
                sell_qty = exchange.position
                entry_price = exchange.avg_entry_price if exchange.avg_entry_price else current_price
                exchange.market_sell(symbol, sell_qty, current_price)
                pnl_pct = (current_price - entry_price) / entry_price
                trades.append({
                    'timestamp': current_time,
                    'type': 'SELL',
                    'price': current_price,
                    'entry_price': entry_price,
                    'quantity': sell_qty,
                    'pnl_pct': pnl_pct,
                    'pnl_usd': (current_price - entry_price) * sell_qty
                })
        
        # Kalan pozisyonu kapat
        if exchange.position > 0:
            final_price = float(df.iloc[-1]['close'])
            final_time = df.index[-1]
            entry_price = exchange.avg_entry_price if exchange.avg_entry_price else final_price
            exchange.market_sell(symbol, exchange.position, final_price)
            pnl_pct = (final_price - entry_price) / entry_price
            trades.append({
                'timestamp': final_time,
                'type': 'FINAL',
                'price': final_price,
                'entry_price': entry_price,
                'quantity': exchange.position,
                'pnl_pct': pnl_pct,
                'pnl_usd': (final_price - entry_price) * exchange.position
            })
        
        final_equity = exchange.cash
        total_return = (final_equity - self.initial_capital) / self.initial_capital
        
        # Trade istatistikleri
        sell_trades = [t for t in trades if t['type'] in ['SELL', 'TAKE_PROFIT', 'STOP_LOSS', 'FINAL']]
        trade_pnl = [t.get('pnl_pct', 0) for t in sell_trades]
        
        profitable = sum(1 for pnl in trade_pnl if pnl > 0)
        win_rate = profitable / len(trade_pnl) if trade_pnl else 0
        
        return {
            'total_return': total_return,
            'final_equity': final_equity,
            'total_trades': len(sell_trades),
            'win_rate': win_rate,
            'trades': trades
        }


class LongTermBacktester:
    """Uzun vadeli strateji - Yıllık kar hedefi"""
    
    def __init__(self, initial_capital: float = 10000.0, commission: float = 0.001):
        self.initial_capital = initial_capital
        self.commission = commission
    
    def run_backtest(self, df: pd.DataFrame, symbol: str):
        """Long-term: Az işlem, geniş stop-loss, yüksek take-profit"""
        
        exchange = PaperExchange(self.initial_capital)
        trades = []
        equity_curve = [self.initial_capital]
        
        # Long-term parametreleri
        stop_loss = 0.10  # %10 stop-loss (geniş)
        take_profit = 0.30  # %30 take-profit (yüksek hedef)
        min_confidence = 0.75  # Daha yüksek confidence (daha az ama kaliteli sinyal)
        position_size = 0.7  # %70 position size (daha büyük pozisyon)
        
        # Trend filtresi (uzun vadeli trend takibi)
        close = df['close'].astype(float)
        ema_50 = close.ewm(span=50).mean()
        ema_200 = close.ewm(span=200).mean()
        
        for i in range(200, len(df)):
            current_data = df.iloc[:i+1]
            current_price = float(current_data.iloc[-1]['close'])
            current_time = df.index[i]
            
            # Trend kontrolü (sadece uptrend'de buy)
            current_ema_50 = ema_50.iloc[i] if i < len(ema_50) else current_price
            current_ema_200 = ema_200.iloc[i] if i < len(ema_200) else current_price
            is_uptrend = current_ema_50 > current_ema_200
            
            signal = compute_bot_hunter_signals(current_data, symbol=symbol)
            current_equity = exchange.cash + (exchange.position * current_price)
            equity_curve.append(current_equity)
            
            # Stop-loss ve take-profit (geniş)
            if exchange.position > 0 and exchange.avg_entry_price:
                pnl_pct = (current_price - exchange.avg_entry_price) / exchange.avg_entry_price
                
                if pnl_pct <= -stop_loss:
                    sell_qty = exchange.position
                    entry_price = exchange.avg_entry_price
                    exchange.market_sell(symbol, sell_qty, current_price)
                    trades.append({
                        'timestamp': current_time,
                        'type': 'STOP_LOSS',
                        'price': current_price,
                        'entry_price': entry_price,
                        'quantity': sell_qty,
                        'pnl_pct': pnl_pct,
                        'pnl_usd': (current_price - entry_price) * sell_qty
                    })
                    continue
                
                if pnl_pct >= take_profit:
                    sell_qty = exchange.position
                    entry_price = exchange.avg_entry_price
                    exchange.market_sell(symbol, sell_qty, current_price)
                    trades.append({
                        'timestamp': current_time,
                        'type': 'TAKE_PROFIT',
                        'price': current_price,
                        'entry_price': entry_price,
                        'quantity': sell_qty,
                        'pnl_pct': pnl_pct,
                        'pnl_usd': (current_price - entry_price) * sell_qty
                    })
                    continue
            
            # Sinyal bazlı işlemler (sadece yüksek confidence + uptrend)
            if signal.side == "buy" and exchange.position <= 0:
                if signal.confidence > min_confidence and is_uptrend:
                    account_balance = exchange.cash + (exchange.position * current_price if exchange.position > 0 else 0)
                    position_value = account_balance * position_size
                    qty = position_value / current_price
                    
                    if qty > 0 and exchange.cash >= position_value * (1 + self.commission):
                        exchange.market_buy(symbol, int(qty * 10000) / 10000, current_price)
                        trades.append({
                            'timestamp': current_time,
                            'type': 'BUY',
                            'price': current_price,
                            'quantity': qty,
                            'confidence': signal.confidence
                        })
            
            elif signal.side == "sell" and exchange.position > 0:
                # Uzun vadeli: Sadece trend kırılırsa veya take-profit'te sat
                if not is_uptrend and signal.confidence > min_confidence:
                    sell_qty = exchange.position
                    entry_price = exchange.avg_entry_price if exchange.avg_entry_price else current_price
                    exchange.market_sell(symbol, sell_qty, current_price)
                    pnl_pct = (current_price - entry_price) / entry_price
                    trades.append({
                        'timestamp': current_time,
                        'type': 'SELL',
                        'price': current_price,
                        'entry_price': entry_price,
                        'quantity': sell_qty,
                        'pnl_pct': pnl_pct,
                        'pnl_usd': (current_price - entry_price) * sell_qty
                    })
        
        # Kalan pozisyonu kapat
        if exchange.position > 0:
            final_price = float(df.iloc[-1]['close'])
            final_time = df.index[-1]
            entry_price = exchange.avg_entry_price if exchange.avg_entry_price else final_price
            exchange.market_sell(symbol, exchange.position, final_price)
            pnl_pct = (final_price - entry_price) / entry_price
            trades.append({
                'timestamp': final_time,
                'type': 'FINAL',
                'price': final_price,
                'entry_price': entry_price,
                'quantity': exchange.position,
                'pnl_pct': pnl_pct,
                'pnl_usd': (final_price - entry_price) * exchange.position
            })
        
        final_equity = exchange.cash
        total_return = (final_equity - self.initial_capital) / self.initial_capital
        
        # Trade istatistikleri
        sell_trades = [t for t in trades if t['type'] in ['SELL', 'TAKE_PROFIT', 'STOP_LOSS', 'FINAL']]
        trade_pnl = [t.get('pnl_pct', 0) for t in sell_trades]
        
        profitable = sum(1 for pnl in trade_pnl if pnl > 0)
        win_rate = profitable / len(trade_pnl) if trade_pnl else 0
        
        return {
            'total_return': total_return,
            'final_equity': final_equity,
            'total_trades': len(sell_trades),
            'win_rate': win_rate,
            'trades': trades
        }


def compare_strategies():
    """Day-trading vs Long-term karşılaştırması"""
    
    print("="*100)
    print("STRATEJİ KARŞILAŞTIRMASI: Day-Trading vs Long-Term")
    print("="*100)
    
    # 1 yıllık veri çek (günlük interval)
    print("\n1 YILLIK VERİ ANALİZİ (Daily Interval)")
    print("-"*100)
    df_daily = fetch_candles("BTC-USD", "1d", 365)
    
    if df_daily.empty or len(df_daily) < 200:
        print("Yetersiz veri!")
        return
    
    print(f"Veri Aralığı: {df_daily.index[0]} - {df_daily.index[-1]}")
    print(f"Toplam Gün: {len(df_daily)}")
    print(f"Başlangıç Fiyatı: ${df_daily.iloc[0]['close']:,.2f}")
    print(f"Bitiş Fiyatı: ${df_daily.iloc[-1]['close']:,.2f}")
    price_change = (df_daily.iloc[-1]['close'] - df_daily.iloc[0]['close']) / df_daily.iloc[0]['close']
    print(f"Fiyat Değişimi: {price_change:+.2%}")
    
    # 1 saatlik veri çek (son 1 ay)
    print("\n1 AYLIK VERİ ANALİZİ (Hourly Interval)")
    print("-"*100)
    df_hourly = fetch_candles("BTC-USD", "1h", 720)
    
    if df_hourly.empty or len(df_hourly) < 200:
        print("Yetersiz veri!")
        return
    
    print(f"Veri Aralığı: {df_hourly.index[0]} - {df_hourly.index[-1]}")
    print(f"Toplam Saat: {len(df_hourly)}")
    
    # Day-trading test (1 saatlik)
    print("\n" + "="*100)
    print("DAY-TRADING STRATEJİSİ (1 Saatlik Interval)")
    print("="*100)
    day_trader = DayTradingBacktester()
    day_result = day_trader.run_backtest(df_hourly, "BTC-USD")
    
    print(f"\nSonuçlar:")
    print(f"  Toplam Getiri: {day_result['total_return']:+.2%}")
    print(f"  Final Equity: ${day_result['final_equity']:,.2f}")
    print(f"  Toplam İşlem: {day_result['total_trades']}")
    print(f"  Kazanma Oranı: {day_result['win_rate']:.1%}")
    
    # Long-term test (günlük)
    print("\n" + "="*100)
    print("LONG-TERM STRATEJİSİ (Günlük Interval)")
    print("="*100)
    long_term = LongTermBacktester()
    long_result = long_term.run_backtest(df_daily, "BTC-USD")
    
    print(f"\nSonuçlar:")
    print(f"  Toplam Getiri: {long_result['total_return']:+.2%}")
    print(f"  Final Equity: ${long_result['final_equity']:,.2f}")
    print(f"  Toplam İşlem: {long_result['total_trades']}")
    print(f"  Kazanma Oranı: {long_result['win_rate']:.1%}")
    
    # Karşılaştırma
    print("\n" + "="*100)
    print("KARŞILAŞTIRMA")
    print("="*100)
    print(f"{'Metrik':<30} {'Day-Trading':<20} {'Long-Term':<20}")
    print("-"*70)
    print(f"{'Toplam Getiri':<30} {day_result['total_return']:+.2%} {'':<15} {long_result['total_return']:+.2%}")
    print(f"{'Final Equity':<30} ${day_result['final_equity']:,.2f} {'':<10} ${long_result['final_equity']:,.2f}")
    print(f"{'Toplam İşlem':<30} {day_result['total_trades']} {'':<15} {long_result['total_trades']}")
    print(f"{'Kazanma Oranı':<30} {day_result['win_rate']:.1%} {'':<15} {long_result['win_rate']:.1%}")
    print(f"{'İşlem Başına Getiri':<30} {(day_result['total_return']/day_result['total_trades']*100) if day_result['total_trades'] > 0 else 0:+.2%} {'':<15} {(long_result['total_return']/long_result['total_trades']*100) if long_result['total_trades'] > 0 else 0:+.2%}")
    
    # Öneri
    print("\n" + "="*100)
    print("ÖNERİ")
    print("="*100)
    
    if day_result['total_return'] > long_result['total_return']:
        print("✅ Day-Trading daha iyi performans gösterdi!")
        print("\nDay-Trading Avantajları:")
        print("  - Daha fazla işlem fırsatı")
        print("  - Hızlı kar realizasyonu")
        print("  - Daha az risk (sıkı stop-loss)")
        print("\nDay-Trading Dezavantajları:")
        print("  - Daha fazla komisyon")
        print("  - Daha fazla zaman gerektirir")
        print("  - Daha fazla stres")
    else:
        print("✅ Long-Term daha iyi performans gösterdi!")
        print("\nLong-Term Avantajları:")
        print("  - Daha az komisyon")
        print("  - Daha az zaman gerektirir")
        print("  - Daha az stres")
        print("  - Trend'i takip eder")
        print("\nLong-Term Dezavantajları:")
        print("  - Daha az işlem fırsatı")
        print("  - Daha yavaş kar realizasyonu")
        print("  - Daha büyük drawdown riski")
    
    # Hibrit öneri
    print("\n" + "="*100)
    print("HİBRİT ÖNERİ")
    print("="*100)
    print("En iyi yaklaşım: İkisini birleştir!")
    print("\n1. Long-Term Core Position (%70):")
    print("   - Uptrend'de buy & hold")
    print("   - %30 take-profit hedefi")
    print("   - %10 stop-loss")
    print("\n2. Day-Trading Swing (%30):")
    print("   - Kısa vadeli fırsatlar")
    print("   - %4 take-profit")
    print("   - %2 stop-loss")
    print("\nBu şekilde hem uzun vadeli kazanç hem de günlük fırsatlar!")


if __name__ == "__main__":
    compare_strategies()

