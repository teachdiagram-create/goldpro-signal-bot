import os
import time
import json
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
import schedule
import logging
import math
from threading import Thread, Lock

# تنظیم لاگ
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# بارگذاری متغیرهای محیطی
load_dotenv()

# تنظیمات
API_KEY = os.getenv("TWELVE_DATA_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# نمادهای معاملاتی
SYMBOLS = {
    "GOLD": {
        "symbol": "XAU/USD",
        "name": "طلا",
        "emoji": "🥇",
        "enabled": True
    },
    "BITCOIN": {
        "symbol": "BTC/USD",
        "name": "بیت کوین",
        "emoji": "₿",
        "enabled": True
    }
}

# پارامترهای استراتژی
EMA_FAST = 9
EMA_SLOW = 21
RSI_PERIOD = 14
ADX_PERIOD = 14
ADX_TREND_LEVEL = 20
ATR_PERIOD = 14

# پارامترهای مخصوص هر نماد
SYMBOL_PARAMS = {
    "GOLD": {
        "RSI_OVERSOLD": 35,
        "RSI_OVERBOUGHT": 65,
        "ATR_MULTIPLIER_SL": 2.0,
        "ATR_MULTIPLIER_TP": 3.0,
        "MIN_CONFIDENCE": 60,
        "STRONG_TREND_ADX": 25  # ADX برای روند قوی
    },
    "BITCOIN": {
        "RSI_OVERSOLD": 30,
        "RSI_OVERBOUGHT": 70,
        "ATR_MULTIPLIER_SL": 2.5,
        "ATR_MULTIPLIER_TP": 3.5,
        "MIN_CONFIDENCE": 65,
        "STRONG_TREND_ADX": 28  # ADX برای روند قوی بیت کوین
    }
}

# مدیریت API
DAILY_LIMIT = 800
MINUTE_LIMIT = 8
SAFE_MARGIN = 0.85
STATE_FILE = "/tmp/api_state.json"
SIGNALS_FILE = "/tmp/signals_history.json"
REPORT_HOUR = 23

# زمان‌بندی
TREND_CHECK_INTERVAL = 5  # دقیقه - بررسی روند
SIGNAL_CHECK_INTERVAL = 1  # دقیقه - بررسی سیگنال در روند قوی

class SignalTracker:
    """مدیریت و پیگیری سیگنال‌ها"""

    def __init__(self):
        self.signals = self.load_signals()
        self.signal_counter = self.load_counter()

    def load_signals(self):
        try:
            with open(SIGNALS_FILE, 'r') as f:
                data = json.load(f)
                today = datetime.now().strftime('%Y-%m-%d')
                if data.get('date') == today:
                    return data.get('signals', [])
                else:
                    return []
        except FileNotFoundError:
            return []

    def load_counter(self):
        try:
            with open(SIGNALS_FILE, 'r') as f:
                data = json.load(f)
                return data.get('total_counter', 0)
        except:
            return 0

    def save_signals(self):
        data = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'signals': self.signals,
            'total_counter': self.signal_counter
        }
        with open(SIGNALS_FILE, 'w') as f:
            json.dump(data, f, indent=2)

    def add_signal(self, symbol_key, signal_type, entry_price, stop_loss, take_profit, confidence, trend, trend_strength):
        self.signal_counter += 1
        symbol_info = SYMBOLS[symbol_key]

        signal_data = {
            'id': self.signal_counter,
            'symbol': symbol_key,
            'symbol_name': symbol_info['name'],
            'symbol_emoji': symbol_info['emoji'],
            'date': datetime.now().strftime('%Y-%m-%d'),
            'time': datetime.now().strftime('%H:%M:%S'),
            'type': signal_type,
            'entry_price': round(entry_price, 2),
            'stop_loss': round(stop_loss, 2),
            'take_profit': round(take_profit, 2),
            'confidence': confidence,
            'trend': trend,
            'trend_strength': trend_strength,
            'status': 'OPEN',
            'result_pips': 0,
            'close_time': None,
            'close_price': None
        }

        self.signals.append(signal_data)
        self.save_signals()
        return signal_data

    def update_signal_status(self, symbol_key, current_price):
        updated = False

        for signal in self.signals:
            if signal['status'] != 'OPEN' or signal['symbol'] != symbol_key:
                continue

            entry = signal['entry_price']
            sl = signal['stop_loss']
            tp = signal['take_profit']

            if signal['type'] == 'BUY':
                if current_price >= tp:
                    signal['status'] = 'WIN'
                    signal['close_price'] = current_price
                    signal['close_time'] = datetime.now().strftime('%H:%M:%S')
                    signal['result_pips'] = round((current_price - entry) * 100, 2)
                    updated = True
                    self.send_signal_close_notification(signal)
                elif current_price <= sl:
                    signal['status'] = 'LOSS'
                    signal['close_price'] = current_price
                    signal['close_time'] = datetime.now().strftime('%H:%M:%S')
                    signal['result_pips'] = round((current_price - entry) * 100, 2)
                    updated = True
                    self.send_signal_close_notification(signal)

            elif signal['type'] == 'SELL':
                if current_price <= tp:
                    signal['status'] = 'WIN'
                    signal['close_price'] = current_price
                    signal['close_time'] = datetime.now().strftime('%H:%M:%S')
                    signal['result_pips'] = round((entry - current_price) * 100, 2)
                    updated = True
                    self.send_signal_close_notification(signal)
                elif current_price >= sl:
                    signal['status'] = 'LOSS'
                    signal['close_price'] = current_price
                    signal['close_time'] = datetime.now().strftime('%H:%M:%S')
                    signal['result_pips'] = round((entry - current_price) * 100, 2)
                    updated = True
                    self.send_signal_close_notification(signal)

        if updated:
            self.save_signals()

        return updated

    def send_signal_close_notification(self, signal):
        emoji = "✅" if signal['status'] == 'WIN' else "❌"
        message = (
            f"{emoji} <b>سیگنال #{signal['id']} بسته شد</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{signal['symbol_emoji']} نماد: {signal['symbol_name']}\n"
            f"📊 نوع: {signal['type']}\n"
            f"💰 قیمت ورود: ${signal['entry_price']:.2f}\n"
            f"💵 قیمت بسته شدن: ${signal['close_price']:.2f}\n"
            f"📈 نتیجه: {signal['result_pips']:+.2f} پیپ\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🕐 {datetime.now().strftime('%H:%M:%S')}"
        )
        send_telegram_message(message)

    def get_daily_report(self):
        if not self.signals:
            return None

        report = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'total_signals': len(self.signals),
            'win_signals': len([s for s in self.signals if s['status'] == 'WIN']),
            'loss_signals': len([s for s in self.signals if s['status'] == 'LOSS']),
            'open_signals': len([s for s in self.signals if s['status'] == 'OPEN']),
            'signals_by_symbol': {},
            'signals_list': self.signals
        }

        total_wins = report['win_signals']
        total_losses = report['loss_signals']
        report['win_rate'] = round((total_wins / (total_wins + total_losses) * 100), 1) if (total_wins + total_losses) > 0 else 0

        for symbol_key in SYMBOLS:
            symbol_signals = [s for s in self.signals if s['symbol'] == symbol_key]
            if not symbol_signals:
                continue

            symbol_wins = [s for s in symbol_signals if s['status'] == 'WIN']
            symbol_losses = [s for s in symbol_signals if s['status'] == 'LOSS']

            report['signals_by_symbol'][symbol_key] = {
                'name': SYMBOLS[symbol_key]['name'],
                'emoji': SYMBOLS[symbol_key]['emoji'],
                'total': len(symbol_signals),
                'wins': len(symbol_wins),
                'losses': len(symbol_losses),
                'win_rate': round((len(symbol_wins) / (len(symbol_wins) + len(symbol_losses)) * 100), 1) if (len(symbol_wins) + len(symbol_losses)) > 0 else 0,
                'total_pips': round(sum(s['result_pips'] for s in symbol_wins + symbol_losses), 2)
            }

        return report

    def format_daily_report(self, report):
        if not report:
            return "📊 امروز سیگنالی صادر نشد."

        message = (
            f"📊 <b>گزارش روزانه ربات</b>\n"
            f"📅 تاریخ: {report['date']}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📈 <b>آمار کلی:</b>\n"
            f"🎯 کل سیگنال‌ها: {report['total_signals']}\n"
            f"✅ سیگنال‌های موفق: {report['win_signals']}\n"
            f"❌ سیگنال‌های ناموفق: {report['loss_signals']}\n"
            f"⏳ سیگنال‌های باز: {report['open_signals']}\n"
            f"📊 نرخ موفقیت: {report['win_rate']}٪\n"
        )

        for symbol_key, stats in report['signals_by_symbol'].items():
            message += (
                f"━━━━━━━━━━━━━━━━━━\n"
                f"{stats['emoji']} <b>{stats['name']}:</b>\n"
                f"🎯 سیگنال‌ها: {stats['total']}\n"
                f"✅ موفق: {stats['wins']} | ❌ ناموفق: {stats['losses']}\n"
                f"📊 نرخ موفقیت: {stats['win_rate']}٪\n"
                f"💰 مجموع پیپ: {stats['total_pips']:+.2f}\n"
            )

        message += f"━━━━━━━━━━━━━━━━━━\n📋 <b>جزئیات سیگنال‌ها:</b>\n"

        for signal in report['signals_list']:
            status_emoji = "✅" if signal['status'] == 'WIN' else "❌" if signal['status'] == 'LOSS' else "⏳"
            result_text = f"{signal['result_pips']:+.2f}" if signal['status'] != 'OPEN' else "در انتظار"

            message += (
                f"{status_emoji} #{signal['id']} | {signal['symbol_emoji']} {signal['symbol_name']} | "
                f"{signal['type']} | نتیجه: {result_text} پیپ\n"
            )

        message += f"━━━━━━━━━━━━━━━━━━\n🕐 {datetime.now().strftime('%H:%M:%S')}"

        return message

class TechnicalIndicators:
    """محاسبه اندیکاتورهای تکنیکال"""

    @staticmethod
    def calculate_ema(data, period):
        if len(data) < period:
            return None
        ema = [sum(data[:period]) / period]
        multiplier = 2 / (period + 1)
        for price in data[period:]:
            ema.append((price - ema[-1]) * multiplier + ema[-1])
        return ema

    @staticmethod
    def calculate_rsi(data, period=14):
        if len(data) < period + 1:
            return None

        gains = []
        losses = []

        for i in range(1, len(data)):
            change = data[i] - data[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))

        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        rsi_values = []
        if avg_loss == 0:
            rsi_values.append(100)
        else:
            rs = avg_gain / avg_loss
            rsi_values.append(100 - (100 / (1 + rs)))

        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period

            if avg_loss == 0:
                rsi_values.append(100)
            else:
                rs = avg_gain / avg_loss
                rsi_values.append(100 - (100 / (1 + rs)))

        return rsi_values

    @staticmethod
    def calculate_atr(highs, lows, closes, period=14):
        if len(closes) < period + 1:
            return None

        tr_values = []
        for i in range(1, len(closes)):
            high = highs[i]
            low = lows[i]
            prev_close = closes[i-1]

            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            tr_values.append(tr)

        atr = [sum(tr_values[:period]) / period]
        for i in range(period, len(tr_values)):
            atr.append((atr[-1] * (period - 1) + tr_values[i]) / period)

        return atr

    @staticmethod
    def calculate_adx(highs, lows, closes, period=14):
        if len(closes) < period * 2:
            return None

        plus_dm = []
        minus_dm = []
        tr_values = []

        for i in range(1, len(closes)):
            high_diff = highs[i] - highs[i-1]
            low_diff = lows[i-1] - lows[i]

            plus_dm.append(max(high_diff, 0) if high_diff > low_diff else 0)
            minus_dm.append(max(low_diff, 0) if low_diff > high_diff else 0)

            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1])
            )
            tr_values.append(tr)

        atr = sum(tr_values[:period]) / period
        plus_di = (sum(plus_dm[:period]) / period) / atr * 100 if atr > 0 else 0
        minus_di = (sum(minus_dm[:period]) / period) / atr * 100 if atr > 0 else 0

        dx_values = []
        for i in range(period, len(tr_values)):
            atr = (atr * (period - 1) + tr_values[i]) / period
            plus_di = ((plus_di * (period - 1) / 100 * atr + plus_dm[i]) / atr) * 100 if atr > 0 else 0
            minus_di = ((minus_di * (period - 1) / 100 * atr + minus_dm[i]) / atr) * 100 if atr > 0 else 0

            if plus_di + minus_di > 0:
                dx = abs(plus_di - minus_di) / (plus_di + minus_di) * 100
            else:
                dx = 0
            dx_values.append(dx)

        adx_values = [sum(dx_values[:period]) / period] if dx_values else [0]
        for i in range(period, len(dx_values)):
            adx_values.append((adx_values[-1] * (period - 1) + dx_values[i]) / period)

        return adx_values, plus_di, minus_di

    @staticmethod
    def calculate_macd(data, fast=12, slow=26, signal=9):
        if len(data) < slow + signal:
            return None, None, None

        ema_fast = TechnicalIndicators.calculate_ema(data, fast)
        ema_slow = TechnicalIndicators.calculate_ema(data, slow)

        if not ema_fast or not ema_slow:
            return None, None, None

        min_length = min(len(ema_fast), len(ema_slow))
        ema_fast = ema_fast[-min_length:]
        ema_slow = ema_slow[-min_length:]

        macd_line = [ema_fast[i] - ema_slow[i] for i in range(min_length)]
        signal_line = TechnicalIndicators.calculate_ema(macd_line, signal)

        if not signal_line:
            return None, None, None

        histogram = [macd_line[i] - signal_line[i] for i in range(len(signal_line))]

        return macd_line, signal_line, histogram

class APIManager:
    """مدیریت هوشمند درخواست‌های API"""

    def __init__(self):
        self.state = self.load_state()
        self.last_request_times = []
        self.signal_tracker = SignalTracker()
        self.last_signal_time = {}
        self.last_report_date = None
        self.trend_state = {}  # وضعیت روند هر نماد
        self.last_trend_check = {}  # زمان آخرین بررسی روند

    def load_state(self):
        try:
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
                if state.get('date') != datetime.now().strftime('%Y-%m-%d'):
                    return {'date': datetime.now().strftime('%Y-%m-%d'), 'requests_today': 0}
                return state
        except FileNotFoundError:
            return {'date': datetime.now().strftime('%Y-%m-%d'), 'requests_today': 0}

    def save_state(self):
        self.state['date'] = datetime.now().strftime('%Y-%m-%d')
        self.state['requests_today'] = self.state.get('requests_today', 0)
        with open(STATE_FILE, 'w') as f:
            json.dump(self.state, f)

    def can_make_request(self):
        now = datetime.now()

        if self.state.get('date') != now.strftime('%Y-%m-%d'):
            self.state = {'date': now.strftime('%Y-%m-%d'), 'requests_today': 0}
            self.last_request_times = []
            self.save_state()

        daily_limit_effective = int(DAILY_LIMIT * SAFE_MARGIN)
        if self.state.get('requests_today', 0) >= daily_limit_effective:
            logger.warning(f"⚠️ نزدیک به سقف روزانه! {self.state['requests_today']}/{daily_limit_effective}")
            return False

        current_minute_requests = [t for t in self.last_request_times if (now - t).total_seconds() < 60]
        if len(current_minute_requests) >= MINUTE_LIMIT - 1:
            wait_time = 60 - (now - current_minute_requests[0]).total_seconds()
            logger.info(f"⏳ محدودیت دقیقه! انتظار {wait_time:.0f} ثانیه")
            return False

        return True

    def record_request(self):
        now = datetime.now()
        self.last_request_times.append(now)
        self.state['requests_today'] = self.state.get('requests_today', 0) + 1
        self.save_state()
        logger.info(f"📊 درخواست #{self.state['requests_today']} امروز")

    def get_status(self):
        usage_percent = (self.state.get('requests_today', 0) / (DAILY_LIMIT * SAFE_MARGIN)) * 100
        return {
            'requests_today': self.state.get('requests_today', 0),
            'daily_limit': int(DAILY_LIMIT * SAFE_MARGIN),
            'usage_percent': usage_percent,
            'is_safe': usage_percent < 80
        }

    def should_send_signal(self, symbol_key, signal_type):