"""
Telegram Bot Signal Sender
Bot sinyallerini otomatik olarak Telegram kanalına gönderir
"""
import asyncio
import os
from datetime import datetime
from typing import Optional
import pandas as pd
from bot.data.yahoo import fetch_candles
from bot.strategy.bot_hunter import compute_bot_hunter_signals
from bot.strategy.ema_rsi_atr import compute_ema_rsi_atr_signals
from bot.strategy.pivot_levels import compute_pivot_levels_signals

try:
    from telegram import Bot
    from telegram.error import TelegramError
except ImportError:
    print("python-telegram-bot kütüphanesi yüklü değil. Yüklemek için: pip install python-telegram-bot")
    Bot = None


class SignalTracker:
    """Sinyal performansını takip eder"""
    def __init__(self):
        self.signals = []
        self.file_path = "signal_history.json"
        self.load_history()
    
    def load_history(self):
        """Geçmiş sinyalleri yükle"""
        import json
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r') as f:
                    self.signals = json.load(f)
            except:
                self.signals = []
    
    def save_history(self):
        """Sinyal geçmişini kaydet"""
        import json
        with open(self.file_path, 'w') as f:
            json.dump(self.signals, f, indent=2)
    
    def add_signal(self, signal_data: dict):
        """Yeni sinyal ekle"""
        signal_data['id'] = len(self.signals) + 1
        signal_data['timestamp'] = datetime.now().isoformat()
        signal_data['status'] = 'open'  # open, closed, stopped
        self.signals.append(signal_data)
        self.save_history()
    
    def update_signal(self, signal_id: int, exit_price: float, exit_reason: str):
        """Sinyali güncelle (kapat)"""
        for signal in self.signals:
            if signal['id'] == signal_id and signal['status'] == 'open':
                signal['exit_price'] = exit_price
                signal['exit_reason'] = exit_reason
                signal['exit_time'] = datetime.now().isoformat()
                signal['status'] = 'closed'
                
                # P&L hesapla
                if signal['side'] == 'buy':
                    pnl_pct = (exit_price - signal['entry_price']) / signal['entry_price'] * 100
                else:
                    pnl_pct = (signal['entry_price'] - exit_price) / signal['entry_price'] * 100
                
                signal['pnl_pct'] = pnl_pct
                signal['pnl_status'] = 'profit' if pnl_pct > 0 else 'loss'
                self.save_history()
                return True
        return False
    
    def get_performance_stats(self):
        """Performans istatistiklerini hesapla"""
        closed_signals = [s for s in self.signals if s.get('status') == 'closed']
        
        if not closed_signals:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'avg_return': 0,
                'total_return': 0
            }
        
        profitable = [s for s in closed_signals if s.get('pnl_pct', 0) > 0]
        win_rate = len(profitable) / len(closed_signals) * 100 if closed_signals else 0
        
        avg_return = sum(s.get('pnl_pct', 0) for s in closed_signals) / len(closed_signals) if closed_signals else 0
        total_return = sum(s.get('pnl_pct', 0) for s in closed_signals)
        
        return {
            'total_trades': len(closed_signals),
            'profitable_trades': len(profitable),
            'losing_trades': len(closed_signals) - len(profitable),
            'win_rate': win_rate,
            'avg_return': avg_return,
            'total_return': total_return
        }


class TelegramSignalSender:
    """Telegram'a sinyal gönderen sınıf"""
    
    def __init__(self, bot_token: str, channel_id: str):
        if Bot is None:
            raise ImportError("python-telegram-bot kütüphanesi yüklü değil")
        
        self.bot = Bot(token=bot_token)
        self.channel_id = channel_id
        self.tracker = SignalTracker()
    
    def format_signal_message(self, symbol: str, signal, current_price: float, 
                            strategy_name: str = "Bot Hunter") -> str:
        """Sinyal mesajını formatla"""
        
        side_emoji = "🚀" if signal.side == "buy" else "📉"
        side_text = "BUY" if signal.side == "buy" else "SELL"
        
        # Target ve stop loss hesapla (basit)
        if signal.side == "buy":
            target_1 = current_price * 1.03  # %3 target
            target_2 = current_price * 1.05  # %5 target
            stop_loss = current_price * 0.98  # %2 stop
        else:
            target_1 = current_price * 0.97  # %3 target
            target_2 = current_price * 0.95  # %5 target
            stop_loss = current_price * 1.02  # %2 stop
        
        message = f"""
{side_emoji} {side_text} SIGNAL
━━━━━━━━━━━━━━━━━━
📊 Symbol: {symbol}
💰 Entry: ${current_price:,.2f}
🎯 Target 1: ${target_1:,.2f} ({((target_1/current_price-1)*100):+.1f}%)
🎯 Target 2: ${target_2:,.2f} ({((target_2/current_price-1)*100):+.1f}%)
🛑 Stop Loss: ${stop_loss:,.2f} ({((stop_loss/current_price-1)*100):+.1f}%)
📈 Strategy: {strategy_name}
🎯 Confidence: {signal.confidence:.0%}
⏰ Time: {datetime.now().strftime('%H:%M UTC')}
━━━━━━━━━━━━━━━━━━
⚠️ RISK WARNING: This is not financial advice. 
Trading involves substantial risk. DYOR.
#CryptoTrading #TradingSignals
"""
        return message.strip()
    
    async def send_signal(self, symbol: str, signal, current_price: float, 
                         strategy_name: str = "Bot Hunter"):
        """Sinyali Telegram'a gönder"""
        try:
            message = self.format_signal_message(symbol, signal, current_price, strategy_name)
            
            # Telegram'a gönder
            await self.bot.send_message(
                chat_id=self.channel_id,
                text=message,
                parse_mode='HTML'
            )
            
            # Sinyali kaydet
            self.tracker.add_signal({
                'symbol': symbol,
                'side': signal.side,
                'entry_price': current_price,
                'strategy': strategy_name,
                'confidence': signal.confidence,
                'reason': getattr(signal, 'reason', 'N/A')
            })
            
            print(f"✅ Sinyal gönderildi: {symbol} {signal.side} @ ${current_price:.2f}")
            return True
            
        except TelegramError as e:
            print(f"❌ Telegram hatası: {e}")
            return False
        except Exception as e:
            print(f"❌ Hata: {e}")
            return False
    
    def get_performance_report(self) -> str:
        """Performans raporu oluştur"""
        stats = self.tracker.get_performance_stats()
        
        if stats['total_trades'] == 0:
            return "Henüz kapatılmış sinyal yok."
        
        report = f"""
📊 PERFORMANCE REPORT
━━━━━━━━━━━━━━━━━━
📈 Total Trades: {stats['total_trades']}
✅ Profitable: {stats['profitable_trades']}
❌ Losing: {stats['losing_trades']}
🎯 Win Rate: {stats['win_rate']:.1f}%
📊 Avg Return: {stats['avg_return']:+.2f}%
💰 Total Return: {stats['total_return']:+.2f}%
━━━━━━━━━━━━━━━━━━
"""
        return report.strip()


async def check_and_send_signals(bot_token: str, channel_id: str, 
                                 symbols: list, interval: str = "1h"):
    """Sinyalleri kontrol et ve gönder"""
    
    sender = TelegramSignalSender(bot_token, channel_id)
    
    print(f"🔍 {len(symbols)} sembol için sinyal kontrol ediliyor...")
    
    for symbol in symbols:
        try:
            # Veri çek
            df = fetch_candles(symbol, interval, 200)
            
            if df.empty or len(df) < 50:
                continue
            
            current_price = float(df.iloc[-1]['close'])
            
            # Bot Hunter stratejisi ile sinyal kontrol et
            signal = compute_bot_hunter_signals(df, symbol=symbol)
            
            # Yüksek confidence sinyalleri gönder
            if signal.side != "hold" and signal.confidence > 0.6:
                await sender.send_signal(
                    symbol=symbol,
                    signal=signal,
                    current_price=current_price,
                    strategy_name="Bot Hunter"
                )
                # Rate limiting için bekle
                await asyncio.sleep(2)
        
        except Exception as e:
            print(f"❌ {symbol} için hata: {e}")
            continue
    
    # Performans raporu gönder (günlük)
    report = sender.get_performance_report()
    if "Henüz kapatılmış sinyal yok" not in report:
        await sender.bot.send_message(
            chat_id=channel_id,
            text=report
        )


def main():
    """Ana fonksiyon - Environment variables'dan token al"""
    
    # Telegram bot token ve channel ID
    BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
    CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID', '')
    
    if not BOT_TOKEN or not CHANNEL_ID:
        print("""
❌ Telegram bot token ve channel ID gerekli!

Kullanım:
1. Telegram'da @BotFather'dan bot oluştur
2. Token'ı al
3. Kanalı oluştur ve bot'u admin yap
4. Channel ID'yi al

Environment variables:
export TELEGRAM_BOT_TOKEN="your_bot_token"
export TELEGRAM_CHANNEL_ID="@your_channel_id"

veya .env dosyası oluştur:
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHANNEL_ID=@your_channel_id
""")
        return
    
    # Test edilecek semboller
    symbols = [
        "BTC-USD",
        "ETH-USD",
        "BNB-USD",
        "SOL-USD",
        "ADA-USD"
    ]
    
    # Sinyalleri kontrol et ve gönder
    asyncio.run(check_and_send_signals(BOT_TOKEN, CHANNEL_ID, symbols))


if __name__ == "__main__":
    main()

