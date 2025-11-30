"""
Kripto Performans Optimizasyonu
Farklı parametreleri test edip en iyisini bulur
"""
import pandas as pd
from bot.data.yahoo import fetch_candles
from bot.strategy.bot_hunter import compute_bot_hunter_signals
from bot.exchange.paper import PaperExchange
from datetime import datetime


class OptimizedBacktester:
    """Optimize edilmiş backtester - kripto için özel"""
    
    def __init__(self, initial_capital: float = 10000.0, commission: float = 0.001):
        self.initial_capital = initial_capital
        self.commission = commission
    
    def run_backtest(self, df: pd.DataFrame, symbol: str, 
                    stop_loss_pct: float = 0.03,
                    take_profit_pct: float = 0.06,
                    min_confidence: float = 0.65,
                    position_size_pct: float = 0.5,
                    use_trend_filter: bool = True) -> dict:
        """Optimize edilmiş backtest"""
        
        if df.empty or len(df) < 50:
            return self._empty_result()
        
        exchange = PaperExchange(self.initial_capital)
        trades = []
        equity_curve = [self.initial_capital]
        
        # Trend filtresi için EMA
        close = df['close'].astype(float)
        ema_50 = close.ewm(span=50).mean()
        ema_200 = close.ewm(span=200).mean()
        
        for i in range(200, len(df)):  # EMA için yeterli veri
            current_data = df.iloc[:i+1]
            current_price = float(current_data.iloc[-1]['close'])
            
            # Trend filtresi
            if use_trend_filter:
                current_ema_50 = ema_50.iloc[i] if i < len(ema_50) else current_price
                current_ema_200 = ema_200.iloc[i] if i < len(ema_200) else current_price
                is_uptrend = current_ema_50 > current_ema_200
            else:
                is_uptrend = True  # Trend filtresi kapalı
            
            # Bot Hunter sinyali
            signal = compute_bot_hunter_signals(current_data, symbol=symbol)
            
            # Mevcut pozisyon kontrolü
            current_equity = exchange.cash + (exchange.position * current_price)
            equity_curve.append(current_equity)
            
            # Stop-loss ve take-profit (daha sıkı)
            if exchange.position > 0 and exchange.avg_entry_price:
                pnl_pct = (current_price - exchange.avg_entry_price) / exchange.avg_entry_price
                
                # Stop-loss
                if pnl_pct <= -stop_loss_pct:
                    sell_qty = exchange.position
                    exchange.market_sell(symbol, sell_qty, current_price)
                    trades.append({
                        'type': 'STOP_LOSS',
                        'price': current_price,
                        'pnl_pct': pnl_pct,
                        'equity': exchange.cash
                    })
                    continue
                
                # Take-profit (daha erken)
                if pnl_pct >= take_profit_pct:
                    sell_qty = exchange.position
                    exchange.market_sell(symbol, sell_qty, current_price)
                    trades.append({
                        'type': 'TAKE_PROFIT',
                        'price': current_price,
                        'pnl_pct': pnl_pct,
                        'equity': exchange.cash
                    })
                    continue
            
            # Sinyal bazlı işlemler (daha yüksek confidence + trend filtresi)
            if signal.side == "buy" and exchange.position <= 0:
                # Trend filtresi + yüksek confidence
                if signal.confidence > min_confidence and (not use_trend_filter or is_uptrend):
                    account_balance = exchange.cash + (exchange.position * current_price if exchange.position > 0 else 0)
                    position_value = account_balance * position_size_pct
                    qty = position_value / current_price
                    
                    if qty > 0 and exchange.cash >= position_value * (1 + self.commission):
                        exchange.market_buy(symbol, int(qty * 10000) / 10000, current_price)
                        trades.append({
                            'type': 'BUY',
                            'price': current_price,
                            'qty': qty,
                            'confidence': signal.confidence,
                            'reason': signal.reason
                        })
            
            elif signal.side == "sell" and exchange.position > 0:
                # Trend filtresi (downtrend'de sat)
                if signal.confidence > min_confidence and (not use_trend_filter or not is_uptrend):
                    sell_qty = exchange.position
                    exchange.market_sell(symbol, sell_qty, current_price)
                    pnl_pct = (current_price - exchange.avg_entry_price) / exchange.avg_entry_price if exchange.avg_entry_price else 0
                    trades.append({
                        'type': 'SELL',
                        'price': current_price,
                        'qty': sell_qty,
                        'pnl_pct': pnl_pct,
                        'confidence': signal.confidence,
                        'reason': signal.reason
                    })
        
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
        
        trade_pnl_pct = []
        buy_idx = 0
        sell_idx = 0
        
        while buy_idx < len(buy_trades) and sell_idx < len(sell_trades):
            buy = buy_trades[buy_idx]
            sell = sell_trades[sell_idx]
            
            if 'pnl_pct' in sell:
                trade_pnl_pct.append(sell['pnl_pct'])
            
            buy_idx += 1
            sell_idx += 1
        
        profitable_trades = sum(1 for pnl in trade_pnl_pct if pnl > 0)
        losing_trades = sum(1 for pnl in trade_pnl_pct if pnl < 0)
        win_rate = profitable_trades / len(trade_pnl_pct) if trade_pnl_pct else 0
        
        # Max drawdown
        equity_series = pd.Series(equity_curve)
        rolling_max = equity_series.expanding().max()
        drawdown = (equity_series - rolling_max) / rolling_max
        max_drawdown = drawdown.min()
        
        return {
            'total_return': total_return,
            'final_equity': final_equity,
            'total_trades': len(trade_pnl_pct),
            'profitable_trades': profitable_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'max_drawdown': max_drawdown,
            'trades': trades
        }
    
    def _empty_result(self):
        return {
            'total_return': 0.0,
            'final_equity': self.initial_capital,
            'total_trades': 0,
            'profitable_trades': 0,
            'losing_trades': 0,
            'win_rate': 0.0,
            'max_drawdown': 0.0
        }


def optimize_crypto(symbol: str):
    """Kripto için en iyi parametreleri bul"""
    
    print(f"\n{'='*80}")
    print(f"OPTIMIZASYON: {symbol}")
    print(f"{'='*80}")
    
    # Veri çek
    df = fetch_candles(symbol, "1h", 720)
    if df.empty or len(df) < 200:
        print(f"Yetersiz veri: {symbol}")
        return None
    
    # Test edilecek parametreler
    stop_loss_options = [0.02, 0.03, 0.04, 0.05]  # %2-5
    take_profit_options = [0.04, 0.06, 0.08, 0.10]  # %4-10
    confidence_options = [0.60, 0.65, 0.70, 0.75]  # %60-75
    position_size_options = [0.3, 0.4, 0.5, 0.6]  # %30-60
    trend_filter_options = [True, False]
    
    best_result = None
    best_params = None
    best_return = float('-inf')
    
    results = []
    
    print("Parametreler test ediliyor...")
    total_tests = len(stop_loss_options) * len(take_profit_options) * len(confidence_options) * len(position_size_options) * len(trend_filter_options)
    test_count = 0
    
    for stop_loss in stop_loss_options:
        for take_profit in take_profit_options:
            for min_conf in confidence_options:
                for pos_size in position_size_options:
                    for use_trend in trend_filter_options:
                        test_count += 1
                        if test_count % 10 == 0:
                            print(f"Test {test_count}/{total_tests}...")
                        
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
                            'win_rate': result['win_rate'],
                            'trades': result['total_trades'],
                            'max_drawdown': result['max_drawdown']
                        })
                        
                        if result['total_return'] > best_return:
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
    print(f"\n{'='*80}")
    print(f"EN İYİ PARAMETRELER: {symbol}")
    print(f"{'='*80}")
    print(f"Stop Loss: {best_params['stop_loss']:.1%}")
    print(f"Take Profit: {best_params['take_profit']:.1%}")
    print(f"Min Confidence: {best_params['min_confidence']:.0%}")
    print(f"Position Size: {best_params['position_size']:.0%}")
    print(f"Trend Filter: {best_params['use_trend']}")
    print(f"\nSonuçlar:")
    print(f"  Getiri: {best_result['total_return']:+.2%}")
    print(f"  Kazanma Oranı: {best_result['win_rate']:.1%}")
    print(f"  Toplam İşlem: {best_result['total_trades']}")
    print(f"  Max Drawdown: {best_result['max_drawdown']:.2%}")
    
    # Top 5 sonuç
    results_sorted = sorted(results, key=lambda x: x['return'], reverse=True)
    print(f"\n{'='*80}")
    print(f"TOP 5 SONUÇ:")
    print(f"{'='*80}")
    for i, r in enumerate(results_sorted[:5], 1):
        print(f"{i}. Return: {r['return']:+.2%} | Win Rate: {r['win_rate']:.1%} | "
              f"SL: {r['stop_loss']:.1%} | TP: {r['take_profit']:.1%} | "
              f"Conf: {r['min_confidence']:.0%} | Size: {r['position_size']:.0%} | "
              f"Trend: {r['use_trend']}")
    
    return best_params, best_result


if __name__ == "__main__":
    # Kripto sembolleri optimize et
    crypto_symbols = ["BTC-USD", "ETH-USD"]
    
    for symbol in crypto_symbols:
        optimize_crypto(symbol)
        print("\n")

