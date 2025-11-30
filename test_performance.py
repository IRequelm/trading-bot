"""
Son 1 Aylık Performans Testi
Bot'un son 1 ayda ne kadar kazandıracağını test eder
"""
import sys
import os
from datetime import datetime, timedelta
import pandas as pd
from bot.data.yahoo import fetch_candles
from bot.backtest.simple_backtester import SimpleBacktester
from bot.backtest.backtester import Backtester
from bot.strategy.ema_rsi_atr import compute_ema_rsi_atr_signals
from bot.strategy.sma import compute_sma_signals
from bot.strategy.pivot_levels import compute_pivot_levels_signals

def test_strategy_performance(symbol: str, interval: str = "1h", strategy_name: str = "pivot"):
    """
    Belirli bir strateji ve sembol için son 1 aylık performans testi
    """
    print(f"\n{'='*60}")
    print(f"TEST: {symbol} - {strategy_name.upper()} Stratejisi")
    print(f"{'='*60}")
    
    # Son 1 ay için veri çek (yaklaşık 30 gün)
    # 1h interval için: 30 gün * 24 saat = 720 bar
    # 5m interval için: 30 gün * 24 saat * 12 = 8640 bar
    lookback = 720 if interval == "1h" else 8640 if interval == "5m" else 720
    
    try:
        df = fetch_candles(symbol, interval, lookback)
        
        if df is None or df.empty:
            print(f"❌ Veri çekilemedi: {symbol}")
            return None
        
        if len(df) < 100:
            print(f"❌ Yetersiz veri: {symbol} (sadece {len(df)} bar)")
            return None
        
        print(f"✅ Veri yüklendi: {len(df)} bar")
        print(f"📅 Tarih aralığı: {df.index[0]} - {df.index[-1]}")
        print(f"💰 Başlangıç fiyatı: ${df.iloc[0]['close']:.2f}")
        print(f"💰 Bitiş fiyatı: ${df.iloc[-1]['close']:.2f}")
        
        # Backtest çalıştır
        initial_capital = 10000.0
        commission = 0.001  # 0.1% komisyon
        
        if strategy_name == "pivot":
            backtester = SimpleBacktester(initial_capital, commission, symbol)
            result = backtester.run_backtest(df, symbol=symbol)
        else:
            # Diğer stratejiler için basit backtester kullan
            backtester = SimpleBacktester(initial_capital, commission, symbol)
            result = backtester.run_backtest(df, symbol=symbol)
        
        # Sonuçları göster
        print(f"\n📊 PERFORMANS SONUÇLARI:")
        print(f"{'─'*60}")
        print(f"Başlangıç Sermayesi:     ${initial_capital:,.2f}")
        print(f"Bitiş Sermayesi:         ${result.final_equity:,.2f}")
        print(f"Toplam Getiri:           {result.total_return:+.2%}")
        print(f"Yıllık Getiri (tahmini): {result.annual_return:+.2%}")
        print(f"Toplam İşlem:            {result.total_trades}")
        print(f"Kazançlı İşlem:          {result.profitable_trades}")
        print(f"Zararlı İşlem:           {result.losing_trades}")
        print(f"Kazanma Oranı:           {result.win_rate:.1%}")
        print(f"Ortalama Kazanç:         ${result.avg_win:.2f}")
        print(f"Ortalama Zarar:          ${result.avg_loss:.2f}")
        print(f"Profit Factor:           {result.profit_factor:.2f}")
        print(f"Max Drawdown:            {result.max_drawdown:.2%}")
        print(f"Sharpe Ratio:            {result.sharpe_ratio:.2f}")
        print(f"{'─'*60}")
        
        # Kar/zarar analizi
        profit = result.final_equity - initial_capital
        if profit > 0:
            print(f"✅ KAR: ${profit:,.2f}")
        else:
            print(f"❌ ZARAR: ${abs(profit):,.2f}")
        
        return result
        
    except Exception as e:
        print(f"❌ Hata: {e}")
        import traceback
        traceback.print_exc()
        return None


def compare_strategies(symbols: list, interval: str = "1h"):
    """
    Birden fazla sembol ve stratejiyi karşılaştır
    """
    print(f"\n{'='*80}")
    print(f"SON 1 AYLIK PERFORMANS KARŞILAŞTIRMASI")
    print(f"Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}")
    
    results = []
    
    for symbol in symbols:
        result = test_strategy_performance(symbol, interval, "pivot")
        if result:
            results.append({
                'symbol': symbol,
                'strategy': 'Pivot Levels',
                'return': result.total_return,
                'final_equity': result.final_equity,
                'trades': result.total_trades,
                'win_rate': result.win_rate,
                'profit_factor': result.profit_factor,
                'max_drawdown': result.max_drawdown,
                'sharpe': result.sharpe_ratio
            })
    
    # Özet tablo
    if results:
        print(f"\n{'='*80}")
        print(f"ÖZET TABLO")
        print(f"{'='*80}")
        print(f"{'Sembol':<12} {'Getiri':<12} {'Bitiş Sermayesi':<18} {'İşlem':<8} {'Kazanma %':<12} {'Profit Factor':<15} {'Max DD':<10}")
        print(f"{'─'*80}")
        
        # Getiriye göre sırala
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
        best = results_sorted[0]
        print(f"\n🏆 EN İYİ PERFORMANS:")
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
    # Test edilecek semboller
    test_symbols = [
        "BTC-USD",   # Bitcoin
        "ETH-USD",   # Ethereum
        "AAPL",      # Apple
        "TSLA",      # Tesla
        "MSFT",      # Microsoft
        "GOOGL",     # Google
    ]
    
    # Interval seçimi (1h veya 5m)
    interval = "1h"  # 1 saatlik mumlar
    
    print("🚀 Tradebot Performans Testi Başlatılıyor...")
    print(f"📅 Test Periyodu: Son 1 Ay")
    print(f"⏱️  Interval: {interval}")
    print(f"💰 Başlangıç Sermayesi: $10,000")
    
    compare_strategies(test_symbols, interval)
    
    print(f"\n{'='*80}")
    print("✅ Test tamamlandı!")
    print(f"{'='*80}")

