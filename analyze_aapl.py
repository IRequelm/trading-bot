"""
AAPL için detaylı analiz - neden sadece 4 işlem?
"""
import pandas as pd
from bot.data.yahoo import fetch_candles
from bot.strategy.bot_hunter import compute_bot_hunter_signals

# AAPL verisi çek
df = fetch_candles("AAPL", "1h", 720)
print(f"AAPL Veri: {len(df)} bar")
print(f"Tarih aralığı: {df.index[0]} - {df.index[-1]}")

# Her bar için sinyal kontrolü
signals = []
total_signals = 0
buy_signals = 0
sell_signals = 0
high_confidence_signals = 0

print("\n" + "="*80)
print("SİNYAL ANALİZİ")
print("="*80)

for i in range(50, len(df), 10):  # Her 10 bar'da bir kontrol (hız için)
    current_data = df.iloc[:i+1]
    signal = compute_bot_hunter_signals(current_data, symbol="AAPL")
    
    total_signals += 1
    
    if signal.side != "hold":
        signals.append({
            'index': i,
            'date': df.index[i],
            'price': float(current_data.iloc[-1]['close']),
            'side': signal.side,
            'confidence': signal.confidence,
            'reason': signal.reason,
            'bot_activity': signal.bot_activity
        })
        
        if signal.side == "buy":
            buy_signals += 1
        else:
            sell_signals += 1
        
        if signal.confidence > 0.6:
            high_confidence_signals += 1

print(f"\nToplam kontrol edilen bar: {total_signals}")
print(f"Toplam sinyal: {len(signals)}")
print(f"Buy sinyalleri: {buy_signals}")
print(f"Sell sinyalleri: {sell_signals}")
print(f"Yüksek confidence (>0.6) sinyalleri: {high_confidence_signals}")

if signals:
    print(f"\n{'='*80}")
    print("DETAYLI SİNYAL LİSTESİ")
    print(f"{'='*80}")
    print(f"{'Tarih':<20} {'Fiyat':<12} {'Sinyal':<6} {'Confidence':<12} {'Sebep':<25} {'Bot Activity':<12}")
    print("-"*80)
    
    for sig in signals[:20]:  # İlk 20 sinyal
        print(f"{str(sig['date']):<20} ${sig['price']:<11.2f} {sig['side']:<6} {sig['confidence']:<12.2f} {sig['reason']:<25} {sig['bot_activity']:<12.2f}")
    
    if len(signals) > 20:
        print(f"... ve {len(signals) - 20} sinyal daha")
else:
    print("\n❌ HİÇ SİNYAL ÜRETİLMEDİ!")
    print("Strateji çok seçici veya confidence threshold çok yüksek olabilir.")

# Confidence dağılımı analizi
print(f"\n{'='*80}")
print("CONFIDENCE DAĞILIMI ANALİZİ")
print(f"{'='*80}")

# Tüm bar'lar için confidence kontrolü
all_confidences = []
for i in range(50, len(df), 5):  # Her 5 bar'da bir
    current_data = df.iloc[:i+1]
    signal = compute_bot_hunter_signals(current_data, symbol="AAPL")
    all_confidences.append(signal.confidence)

if all_confidences:
    conf_series = pd.Series(all_confidences)
    print(f"Ortalama confidence: {conf_series.mean():.3f}")
    print(f"Max confidence: {conf_series.max():.3f}")
    print(f"Min confidence: {conf_series.min():.3f}")
    print(f"Confidence > 0.6 olanlar: {(conf_series > 0.6).sum()} / {len(conf_series)}")
    print(f"Confidence > 0.5 olanlar: {(conf_series > 0.5).sum()} / {len(conf_series)}")
    print(f"Confidence > 0.4 olanlar: {(conf_series > 0.4).sum()} / {len(conf_series)}")

