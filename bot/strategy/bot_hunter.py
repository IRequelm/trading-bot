"""
Bot Hunter Strategy - Bot davranışlarını tespit edip onlardan faydalanan strateji

Bu strateji şu prensiplere dayanır:
1. Botlar büyük volume spike'ları yaratır - bunları tespit edip takip ederiz
2. Botlar aşırı hareketler yaratır - mean reversion fırsatları
3. Botlar belirli pattern'leri takip eder - bu pattern'leri önceden yakalarız
4. Liquidity hunting - botlar stop-loss'ları avlar, biz de onları avlarız
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Optional


@dataclass
class BotHunterSignal:
    side: str  # 'buy', 'sell', 'hold'
    confidence: float
    reason: str  # Neden bu sinyal verildi
    bot_activity: float  # Bot aktivite seviyesi (0-1)


def detect_bot_activity(df: pd.DataFrame, lookback: int = 20) -> pd.Series:
    """
    Bot aktivitesini tespit eder:
    - Anormal volume artışları
    - Düzenli pattern'ler
    - Hızlı fiyat değişimleri
    """
    if df.empty or len(df) < lookback:
        return pd.Series([0.0] * len(df), index=df.index)
    
    volume = df['volume'].astype(float)
    close = df['close'].astype(float)
    high = df['high'].astype(float)
    low = df['low'].astype(float)
    
    # 1. Volume spike detection (botlar büyük işlemler yapar)
    volume_ma = volume.rolling(window=lookback).mean()
    volume_std = volume.rolling(window=lookback).std()
    volume_zscore = (volume - volume_ma) / (volume_std + 1e-10)
    volume_spike = (volume_zscore > 2.0).astype(float)  # 2 std üstü
    
    # 2. Price volatility spike (botlar hızlı hareketler yaratır)
    price_change = close.pct_change().abs()
    volatility_ma = price_change.rolling(window=lookback).mean()
    volatility_spike = (price_change > volatility_ma * 2.0).astype(float)
    
    # 3. Regular pattern detection (botlar düzenli pattern'ler yaratır) - OPTIMIZED
    # Rolling window ile vectorized hesaplama
    pattern_std = price_change.rolling(window=lookback).std()
    pattern_score = (1.0 / (pattern_std + 0.001)).clip(0, 100) / 100
    
    # 4. Liquidity hunting detection (botlar stop-loss'ları avlar) - OPTIMIZED
    # Rolling min ile vectorized hesaplama
    rolling_low_5 = low.rolling(window=5).min()
    liquidity_hunt = ((rolling_low_5 < close * 0.98).astype(float))
    
    # Kombine bot aktivite skoru
    bot_activity = (
        volume_spike * 0.3 +
        volatility_spike * 0.3 +
        pattern_score * 0.2 +
        liquidity_hunt * 0.2
    )
    
    return bot_activity


def compute_bot_hunter_signals(df: pd.DataFrame, symbol: str = "") -> BotHunterSignal:
    """
    Bot Hunter Strategy - Bot davranışlarını tespit edip onlardan faydalanır
    
    Strateji mantığı:
    1. Bot aktivitesi yüksekken bekle (botlar işlem yapıyor)
    2. Botlar aşırı hareket yarattıktan sonra mean reversion bekle
    3. Volume spike sonrası momentum takip et
    4. Liquidity hunt sonrası ters yönde pozisyon al
    """
    if df.empty or len(df) < 50:
        return BotHunterSignal(side="hold", confidence=0.0, reason="Yetersiz veri", bot_activity=0.0)
    
    close = df['close'].astype(float)
    high = df['high'].astype(float)
    low = df['low'].astype(float)
    volume = df['volume'].astype(float)
    
    # Bot aktivitesini tespit et
    bot_activity = detect_bot_activity(df, lookback=20)
    current_bot_activity = bot_activity.iloc[-1] if len(bot_activity) > 0 else 0.0
    
    # Teknik göstergeler
    # RSI
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    current_rsi = rsi.iloc[-1]
    
    # Bollinger Bands (mean reversion için)
    sma_20 = close.rolling(window=20).mean()
    std_20 = close.rolling(window=20).std()
    bb_upper = sma_20 + (std_20 * 2)
    bb_lower = sma_20 - (std_20 * 2)
    bb_width = (bb_upper - bb_lower) / sma_20
    
    current_price = close.iloc[-1]
    current_sma = sma_20.iloc[-1]
    current_bb_upper = bb_upper.iloc[-1]
    current_bb_lower = bb_lower.iloc[-1]
    current_bb_width = bb_width.iloc[-1]
    
    # Volume analizi
    volume_ma = volume.rolling(window=20).mean()
    current_volume = volume.iloc[-1]
    current_volume_ma = volume_ma.iloc[-1]
    volume_ratio = current_volume / (current_volume_ma + 1e-10)
    
    # EMA'lar (trend takibi)
    ema_fast = close.ewm(span=12).mean()
    ema_slow = close.ewm(span=26).mean()
    current_ema_fast = ema_fast.iloc[-1]
    current_ema_slow = ema_slow.iloc[-1]
    prev_ema_fast = ema_fast.iloc[-2] if len(ema_fast) > 1 else current_ema_fast
    prev_ema_slow = ema_slow.iloc[-2] if len(ema_slow) > 1 else current_ema_slow
    
    # NaN kontrolü
    if pd.isna(current_rsi) or pd.isna(current_sma) or pd.isna(current_bb_width):
        return BotHunterSignal(side="hold", confidence=0.0, reason="Gösterge hesaplanamadı", bot_activity=current_bot_activity)
    
    # STRATEJİ 1: Mean Reversion (Botlar aşırı hareket yaratır, sonra fiyat normale döner)
    # Daha esnek koşullar - sadece BB sapması veya RSI yeterli
    bb_distance_buy = (current_price - current_bb_lower) / (current_bb_upper - current_bb_lower + 1e-10)
    bb_distance_sell = (current_price - current_bb_lower) / (current_bb_upper - current_bb_lower + 1e-10)
    
    mean_reversion_buy = (
        (current_price <= current_bb_lower * 1.01 or current_rsi < 35) and  # Alt banda yakın veya oversold
        current_rsi < 40 and  # Oversold bölgesinde
        current_bb_width > 0.01  # Minimum volatilite
    )
    
    mean_reversion_sell = (
        (current_price >= current_bb_upper * 0.99 or current_rsi > 65) and  # Üst banda yakın veya overbought
        current_rsi > 60 and  # Overbought bölgesinde
        current_bb_width > 0.01  # Minimum volatilite
    )
    
    # STRATEJİ 2: Volume Spike Momentum (Botlar büyük işlem yaptıktan sonra momentum takip)
    # Daha esnek - volume spike veya EMA trend yeterli
    volume_spike = volume_ratio > 1.3  # %30 üstü volume (daha düşük threshold)
    ema_bullish_cross = prev_ema_fast <= prev_ema_slow and current_ema_fast > current_ema_slow
    ema_bearish_cross = prev_ema_fast >= prev_ema_slow and current_ema_fast < current_ema_slow
    ema_bullish = current_ema_fast > current_ema_slow  # Trend yönü
    ema_bearish = current_ema_fast < current_ema_slow
    
    momentum_buy = (
        (volume_spike or ema_bullish_cross or ema_bullish) and  # Volume spike VEYA EMA trend
        current_rsi > 35 and current_rsi < 75 and  # Daha geniş RSI aralığı
        current_price > current_sma * 0.995  # SMA'ya yakın olması yeterli
    )
    
    momentum_sell = (
        (volume_spike or ema_bearish_cross or ema_bearish) and  # Volume spike VEYA EMA trend
        current_rsi < 65 and current_rsi > 25 and  # Daha geniş RSI aralığı
        current_price < current_sma * 1.005  # SMA'ya yakın olması yeterli
    )
    
    # STRATEJİ 3: Liquidity Hunt Reversal (Botlar stop-loss avladıktan sonra ters yön)
    # Daha esnek - daha küçük hareketler de kabul edilir
    recent_low = low.iloc[-5:].min()
    recent_high = high.iloc[-5:].max()
    price_recovery = (current_price - recent_low) / (recent_high - recent_low + 1e-10)
    
    liquidity_reversal_buy = (
        recent_low < current_price * 0.995 and  # Son 5 bar'da %0.5+ düşüş (daha düşük threshold)
        price_recovery > 0.3 and  # Kısmi toparlanma yeterli
        current_rsi < 55  # Henüz aşırı alım değil
    )
    
    liquidity_reversal_sell = (
        recent_high > current_price * 1.005 and  # Son 5 bar'da %0.5+ yükseliş
        price_recovery < 0.7 and  # Kısmi düşüş yeterli
        current_rsi > 45  # Henüz aşırı satım değil
    )
    
    # STRATEJİ 4: Bot Activity Fade (Bot aktivitesi azaldığında trend takip)
    # Daha esnek - bot aktivitesi düşükken de işlem yapabilir
    prev_bot_activity = bot_activity.iloc[-2] if len(bot_activity) > 1 else 0.0
    bot_activity_decreasing = current_bot_activity < prev_bot_activity and prev_bot_activity > 0.3  # Daha düşük threshold
    bot_activity_low = current_bot_activity < 0.4  # Düşük bot aktivitesi
    
    bot_fade_buy = (
        (bot_activity_decreasing or bot_activity_low) and  # Aktivite düşüyor VEYA düşük
        (current_ema_fast > current_ema_slow or current_price > current_sma) and  # Trend veya fiyat pozitif
        current_rsi > 40 and current_rsi < 70  # Daha geniş RSI aralığı
    )
    
    bot_fade_sell = (
        (bot_activity_decreasing or bot_activity_low) and  # Aktivite düşüyor VEYA düşük
        (current_ema_fast < current_ema_slow or current_price < current_sma) and  # Trend veya fiyat negatif
        current_rsi < 60 and current_rsi > 30  # Daha geniş RSI aralığı
    )
    
    # Sinyal önceliklendirme ve confidence hesaplama
    buy_signals = []
    sell_signals = []
    
    if mean_reversion_buy:
        # Daha cömert confidence - minimum 0.4
        rsi_factor = max(0, (40 - current_rsi) / 40)  # RSI ne kadar düşükse o kadar yüksek confidence
        bb_factor = max(0, (current_bb_lower - current_price) / (current_bb_upper - current_bb_lower + 1e-10))
        confidence = min(0.85, 0.4 + rsi_factor * 0.3 + bb_factor * 0.15)
        buy_signals.append(("Mean Reversion", confidence))
    
    if momentum_buy:
        # Volume veya EMA trend'e göre confidence
        vol_factor = min(1.0, (volume_ratio - 1.0) / 0.5) if volume_spike else 0.3
        ema_factor = 0.4 if ema_bullish_cross else (0.2 if ema_bullish else 0.1)
        confidence = min(0.90, 0.4 + vol_factor * 0.3 + ema_factor * 0.2)
        buy_signals.append(("Volume Momentum", confidence))
    
    if liquidity_reversal_buy:
        recovery_factor = max(0, price_recovery - 0.3) / 0.7
        confidence = min(0.80, 0.4 + recovery_factor * 0.4)
        buy_signals.append(("Liquidity Reversal", confidence))
    
    if bot_fade_buy:
        activity_factor = max(0, (prev_bot_activity - current_bot_activity)) if bot_activity_decreasing else 0.3
        confidence = min(0.75, 0.4 + activity_factor * 0.35)
        buy_signals.append(("Bot Fade", confidence))
    
    if mean_reversion_sell:
        confidence = min(0.85, 0.5 + (current_rsi - 70) / 30 * 0.35)
        sell_signals.append(("Mean Reversion", confidence))
    
    if momentum_sell:
        confidence = min(0.90, 0.6 + volume_ratio / 3 * 0.3)
        sell_signals.append(("Volume Momentum", confidence))
    
    if liquidity_reversal_sell:
        confidence = min(0.80, 0.5 + (1 - price_recovery) * 0.3)
        sell_signals.append(("Liquidity Reversal", confidence))
    
    if bot_fade_sell:
        confidence = min(0.75, 0.5 + (prev_bot_activity - current_bot_activity) * 0.5)
        sell_signals.append(("Bot Fade", confidence))
    
    # En yüksek confidence'lı sinyali seç
    if buy_signals:
        best_buy = max(buy_signals, key=lambda x: x[1])
        return BotHunterSignal(
            side="buy",
            confidence=best_buy[1],
            reason=best_buy[0],
            bot_activity=current_bot_activity
        )
    
    if sell_signals:
        best_sell = max(sell_signals, key=lambda x: x[1])
        return BotHunterSignal(
            side="sell",
            confidence=best_sell[1],
            reason=best_sell[0],
            bot_activity=current_bot_activity
        )
    
    # Bot aktivitesi çok yüksekse bekle (botlar işlem yapıyor, karışıklık var)
    if current_bot_activity > 0.7:
        return BotHunterSignal(
            side="hold",
            confidence=0.3,
            reason="Yüksek bot aktivitesi - bekle",
            bot_activity=current_bot_activity
        )
    
    return BotHunterSignal(
        side="hold",
        confidence=0.2,
        reason="Sinyal yok",
        bot_activity=current_bot_activity
    )

