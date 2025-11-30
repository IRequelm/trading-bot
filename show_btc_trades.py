"""
BTC için detaylı işlem listesi
"""
import pandas as pd
from datetime import datetime
from bot.data.yahoo import fetch_candles
from bot.strategy.bot_hunter import compute_bot_hunter_signals
from bot.exchange.paper import PaperExchange


class DetailedBacktester:
    """Detaylı işlem listesi için backtester"""
    
    def __init__(self, initial_capital: float = 10000.0, commission: float = 0.001):
        self.initial_capital = initial_capital
        self.commission = commission
    
    def run_backtest(self, df: pd.DataFrame, symbol: str):
        """Detaylı backtest - tüm işlemleri kaydet"""
        
        if df.empty or len(df) < 50:
            return []
        
        exchange = PaperExchange(self.initial_capital)
        trades = []
        equity_curve = [self.initial_capital]
        
        # Trend filtresi için EMA
        close = df['close'].astype(float)
        ema_50 = close.ewm(span=50).mean()
        ema_200 = close.ewm(span=200).mean()
        
        for i in range(200, len(df)):
            current_data = df.iloc[:i+1]
            current_price = float(current_data.iloc[-1]['close'])
            current_time = df.index[i]
            
            # Trend filtresi
            current_ema_50 = ema_50.iloc[i] if i < len(ema_50) else current_price
            current_ema_200 = ema_200.iloc[i] if i < len(ema_200) else current_price
            is_uptrend = current_ema_50 > current_ema_200
            
            # Bot Hunter sinyali
            signal = compute_bot_hunter_signals(current_data, symbol=symbol)
            
            # Mevcut pozisyon kontrolü
            current_equity = exchange.cash + (exchange.position * current_price)
            equity_curve.append(current_equity)
            
            # Stop-loss ve take-profit (kripto için optimize edilmiş)
            if exchange.position > 0 and exchange.avg_entry_price:
                pnl_pct = (current_price - exchange.avg_entry_price) / exchange.avg_entry_price
                
                # Kripto: %3 stop-loss, %6 take-profit
                stop_loss = 0.03
                take_profit = 0.06
                
                # Stop-loss
                if pnl_pct <= -stop_loss:
                    sell_qty = exchange.position
                    entry_price = exchange.avg_entry_price if exchange.avg_entry_price else current_price
                    exchange.market_sell(symbol, sell_qty, current_price)
                    pnl_usd = (current_price - entry_price) * sell_qty
                    trades.append({
                        'timestamp': current_time,
                        'type': 'STOP_LOSS',
                        'side': 'SELL',
                        'price': current_price,
                        'quantity': sell_qty,
                        'pnl_pct': pnl_pct,
                        'pnl_usd': pnl_usd,
                        'equity': exchange.cash,
                        'reason': f'Stop-loss triggered ({pnl_pct:.2%})',
                        'confidence': 1.0,
                        'entry_price': entry_price
                    })
                    continue
                
                # Take-profit
                if pnl_pct >= take_profit:
                    sell_qty = exchange.position
                    entry_price = exchange.avg_entry_price if exchange.avg_entry_price else current_price
                    exchange.market_sell(symbol, sell_qty, current_price)
                    pnl_usd = (current_price - entry_price) * sell_qty
                    trades.append({
                        'timestamp': current_time,
                        'type': 'TAKE_PROFIT',
                        'side': 'SELL',
                        'price': current_price,
                        'quantity': sell_qty,
                        'pnl_pct': pnl_pct,
                        'pnl_usd': pnl_usd,
                        'equity': exchange.cash,
                        'reason': f'Take-profit triggered ({pnl_pct:.2%})',
                        'confidence': 1.0,
                        'entry_price': entry_price
                    })
                    continue
            
            # Sinyal bazlı işlemler
            is_crypto = symbol.endswith('-USD') and symbol not in ['AAPL', 'TSLA', 'MSFT', 'GOOGL']
            min_confidence = 0.70 if is_crypto else 0.4
            
            if signal.side == "buy" and exchange.position <= 0 and signal.confidence > min_confidence:
                # Kripto için sadece uptrend'de buy yap
                if is_crypto and not is_uptrend:
                    continue
                
                account_balance = exchange.cash + (exchange.position * current_price if exchange.position > 0 else 0)
                if is_crypto:
                    position_size_pct = min(0.4, signal.confidence * 0.6)
                else:
                    position_size_pct = min(0.7, signal.confidence)
                position_value = account_balance * position_size_pct
                qty = position_value / current_price
                
                if qty > 0 and exchange.cash >= position_value * (1 + self.commission):
                    exchange.market_buy(symbol, int(qty * 10000) / 10000, current_price)
                    trades.append({
                        'timestamp': current_time,
                        'type': 'BUY',
                        'side': 'BUY',
                        'price': current_price,
                        'quantity': qty,
                        'pnl_pct': 0.0,
                        'pnl_usd': 0.0,
                        'equity': exchange.cash + (exchange.position * current_price),
                        'reason': signal.reason,
                        'confidence': signal.confidence,
                        'entry_price': current_price
                    })
            
            elif signal.side == "sell" and exchange.position > 0 and signal.confidence > min_confidence:
                sell_qty = exchange.position
                entry_price = exchange.avg_entry_price if exchange.avg_entry_price else current_price
                exchange.market_sell(symbol, sell_qty, current_price)
                pnl_pct = (current_price - entry_price) / entry_price
                pnl_usd = (current_price - entry_price) * sell_qty
                trades.append({
                    'timestamp': current_time,
                    'type': 'SELL',
                    'side': 'SELL',
                    'price': current_price,
                    'quantity': sell_qty,
                    'pnl_pct': pnl_pct,
                    'pnl_usd': pnl_usd,
                    'equity': exchange.cash,
                    'reason': signal.reason,
                    'confidence': signal.confidence,
                    'entry_price': entry_price
                })
        
        # Kalan pozisyonu kapat
        if exchange.position > 0:
            final_price = float(df.iloc[-1]['close'])
            final_time = df.index[-1]
            entry_price = exchange.avg_entry_price if exchange.avg_entry_price else final_price
            exchange.market_sell(symbol, exchange.position, final_price)
            pnl_pct = (final_price - entry_price) / entry_price
            pnl_usd = (final_price - entry_price) * exchange.position
            trades.append({
                'timestamp': final_time,
                'type': 'FINAL',
                'side': 'SELL',
                'price': final_price,
                'quantity': exchange.position,
                'pnl_pct': pnl_pct,
                'pnl_usd': pnl_usd,
                'equity': exchange.cash,
                'reason': 'Final liquidation',
                'confidence': 0.0,
                'entry_price': entry_price
            })
        
        return trades


def show_btc_trades():
    """BTC için tüm işlemleri göster"""
    
    print("="*100)
    print("BTC-USD İŞLEM LİSTESİ - Son 1 Ay")
    print("="*100)
    
    # Veri çek
    df = fetch_candles("BTC-USD", "1h", 720)
    
    if df.empty or len(df) < 200:
        print("Yetersiz veri!")
        return
    
    print(f"\nVeri Aralığı: {df.index[0]} - {df.index[-1]}")
    print(f"Toplam Bar: {len(df)}")
    print(f"Başlangıç Fiyatı: ${df.iloc[0]['close']:,.2f}")
    print(f"Bitiş Fiyatı: ${df.iloc[-1]['close']:,.2f}")
    
    # Backtest çalıştır
    backtester = DetailedBacktester(initial_capital=10000.0, commission=0.001)
    trades = backtester.run_backtest(df, "BTC-USD")
    
    if not trades:
        print("\nHiç işlem yapılmadı!")
        return
    
    print(f"\n{'='*100}")
    print(f"TOPLAM İŞLEM SAYISI: {len(trades)}")
    print(f"{'='*100}\n")
    
    # İşlemleri göster
    print(f"{'Tarih':<20} {'Tip':<12} {'Fiyat':<15} {'Entry':<15} {'Miktar':<15} {'P&L %':<12} {'P&L $':<15} {'Sebep':<25} {'Conf':<8}")
    print("-"*120)
    
    total_pnl = 0
    buy_trades = []
    sell_trades = []
    
    for trade in trades:
        timestamp = str(trade['timestamp'])[:19] if hasattr(trade['timestamp'], '__str__') else str(trade['timestamp'])
        trade_type = trade['type']
        price = trade['price']
        entry_price = trade.get('entry_price', price)
        qty = trade['quantity']
        pnl_pct = trade['pnl_pct']
        pnl_usd = trade.get('pnl_usd', 0)
        reason = trade.get('reason', 'N/A')
        confidence = trade.get('confidence', 0.0)
        
        # P&L işareti
        if pnl_pct > 0:
            pnl_str = f"+{pnl_pct:.2%}"
            pnl_usd_str = f"+${pnl_usd:.2f}"
        elif pnl_pct < 0:
            pnl_str = f"{pnl_pct:.2%}"
            pnl_usd_str = f"-${abs(pnl_usd):.2f}"
        else:
            pnl_str = "0.00%"
            pnl_usd_str = "$0.00"
        
        # Entry price göster (sadece SELL işlemlerinde)
        if trade_type == 'BUY':
            entry_str = "-"
        else:
            entry_str = f"${entry_price:,.2f}"
        
        print(f"{timestamp:<20} {trade_type:<12} ${price:<14,.2f} {entry_str:<15} {qty:<15.6f} {pnl_str:<12} {pnl_usd_str:<15} {reason:<25} {confidence:.0%}")
        
        if trade_type == 'BUY':
            buy_trades.append(trade)
        elif trade_type in ['SELL', 'TAKE_PROFIT', 'STOP_LOSS', 'FINAL']:
            sell_trades.append(trade)
            total_pnl += pnl_usd
    
    # Özet
    print(f"\n{'='*100}")
    print("ÖZET")
    print(f"{'='*100}")
    print(f"Toplam BUY İşlemi: {len(buy_trades)}")
    print(f"Toplam SELL İşlemi: {len(sell_trades)}")
    print(f"Toplam P&L: ${total_pnl:,.2f}")
    print(f"Final Equity: ${trades[-1]['equity']:,.2f}")
    print(f"Toplam Getiri: {((trades[-1]['equity'] - 10000) / 10000):+.2%}")
    
    # Kazançlı/Zararlı işlemler
    profitable = [t for t in sell_trades if t.get('pnl_pct', 0) > 0]
    losing = [t for t in sell_trades if t.get('pnl_pct', 0) < 0]
    
    print(f"\nKazançlı İşlem: {len(profitable)}")
    print(f"Zararlı İşlem: {len(losing)}")
    if len(sell_trades) > 0:
        print(f"Kazanma Oranı: {len(profitable) / len(sell_trades):.1%}")
    
    # En iyi/En kötü işlemler
    if profitable:
        best = max(profitable, key=lambda x: x.get('pnl_pct', 0))
        print(f"\nEn İyi İşlem: {best['timestamp']} | {best['pnl_pct']:+.2%} | ${best.get('pnl_usd', 0):,.2f}")
    
    if losing:
        worst = min(losing, key=lambda x: x.get('pnl_pct', 0))
        print(f"En Kötü İşlem: {worst['timestamp']} | {worst['pnl_pct']:.2%} | ${worst.get('pnl_usd', 0):,.2f}")


if __name__ == "__main__":
    show_btc_trades()

