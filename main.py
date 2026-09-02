import os
import time
import json
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
import schedule
import logging
import math

# تنظیم لاگ
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# بارگذاری متغیرهای محیطی
load_dotenv()

# منطقه زمانی ایران
IRAN_TZ = ZoneInfo("Asia/Tehran")

def get_iran_time():
    return datetime.now(IRAN_TZ)

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
        "enabled": false
    }
}

# پارامترهای استراتژی
EMA_FAST = 5
EMA_SLOW = 13
RSI_PERIOD = 14
ADX_PERIOD = 14
ADX_TREND_LEVEL = 18
ATR_PERIOD = 14

# پارامترهای مخصوص هر نماد (به‌روزرسانی شده)
SYMBOL_PARAMS = {
    "GOLD": {
        "RSI_OVERSOLD": 35,
        "RSI_OVERBOUGHT": 65,
        "ATR_MULTIPLIER_SL": 3.5,
        "ATR_MULTIPLIER_TP": 5.0,
        "MIN_CONFIDENCE": 60,
        "STRONG_TREND_ADX": 25
    },
    "BITCOIN": {
        "RSI_OVERSOLD": 30,
        "RSI_OVERBOUGHT": 70,
        "ATR_MULTIPLIER_SL": 3.5,
        "ATR_MULTIPLIER_TP": 5.0,
        "MIN_CONFIDENCE": 65,
        "STRONG_TREND_ADX": 30
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
TREND_CHECK_INTERVAL = 5
SIGNAL_CHECK_INTERVAL = 1


class SignalTracker:
    def __init__(self):
        self.signals = self.load_signals()
        self.signal_counter = self.load_counter()

    def load_signals(self):
        try:
            with open(SIGNALS_FILE, 'r') as f:
                data = json.load(f)
                today = get_iran_time().strftime('%Y-%m-%d')
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
            'date': get_iran_time().strftime('%Y-%m-%d'),
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
            'date': get_iran_time().strftime('%Y-%m-%d'),
            'time': get_iran_time().strftime('%H:%M:%S'),
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
                    signal['close_time'] = get_iran_time().strftime('%H:%M:%S')
                    signal['result_pips'] = round((current_price - entry) * 100, 2)
                    updated = True
                    self.send_signal_close_notification(signal)
                elif current_price <= sl:
                    signal['status'] = 'LOSS'
                    signal['close_price'] = current_price
                    signal['close_time'] = get_iran_time().strftime('%H:%M:%S')
                    signal['result_pips'] = round((current_price - entry) * 100, 2)
                    updated = True
                    self.send_signal_close_notification(signal)

            elif signal['type'] == 'SELL':
                if current_price <= tp:
                    signal['status'] = 'WIN'
                    signal['close_price'] = current_price
                    signal['close_time'] = get_iran_time().strftime('%H:%M:%S')
                    signal['result_pips'] = round((entry - current_price) * 100, 2)
                    updated = True
                    self.send_signal_close_notification(signal)
                elif current_price >= sl:
                    signal['status'] = 'LOSS'
                    signal['close_price'] = current_price
                    signal['close_time'] = get_iran_time().strftime('%H:%M:%S')
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
            f"🕐 {get_iran_time().strftime('%H:%M:%S')}"
        )
        send_telegram_message(message)

    def get_daily_report(self):
        if not self.signals:
            return None

        report = {
            'date': get_iran_time().strftime('%Y-%m-%d'),
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

        message += f"━━━━━━━━━━━━━━━━━━\n🕐 {get_iran_time().strftime('%H:%M:%S')}"

        return message
class TechnicalIndicators:
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
    def __init__(self):
        self.state = self.load_state()
        self.last_request_times = []
        self.signal_tracker = SignalTracker()
        self.last_signal_time = {}
        self.last_report_date = None
        self.trend_state = {}
        self.last_trend_check = {}

    def load_state(self):
        try:
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
                if state.get('date') != get_iran_time().strftime('%Y-%m-%d'):
                    return {'date': get_iran_time().strftime('%Y-%m-%d'), 'requests_today': 0}
                return state
        except FileNotFoundError:
            return {'date': get_iran_time().strftime('%Y-%m-%d'), 'requests_today': 0}

    def save_state(self):
        self.state['date'] = get_iran_time().strftime('%Y-%m-%d')
        self.state['requests_today'] = self.state.get('requests_today', 0)
        with open(STATE_FILE, 'w') as f:
            json.dump(self.state, f)

    def can_make_request(self):
        now = get_iran_time()

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
        now = get_iran_time()
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
        current_time = time.time()
        key = f"{symbol_key}_{signal_type}"
        last_time = self.last_signal_time.get(key, 0)

        if current_time - last_time < 1800:
            return False

        self.last_signal_time[key] = current_time
        return True

    def should_check_trend(self, symbol_key):
        now = time.time()
        last_check = self.last_trend_check.get(symbol_key, 0)

        if now - last_check >= TREND_CHECK_INTERVAL * 60:
            self.last_trend_check[symbol_key] = now
            return True
        return False

    def should_check_signal(self, symbol_key):
        trend_info = self.trend_state.get(symbol_key, {})
        if trend_info.get('is_strong', False):
            return True
        return False
def send_telegram_message(text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("تنظیمات تلگرام کامل نیست")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}

    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code != 200:
            logger.error(f"خطا در ارسال تلگرام: {response.text}")
        return response.status_code == 200
    except Exception as e:
        logger.error(f"استثنا در ارسال تلگرام: {e}")
        return False


def get_market_data(api_manager, symbol_key, interval="5min", outputsize=100):
    if not api_manager.can_make_request():
        return None

    symbol = SYMBOLS[symbol_key]["symbol"]
    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": symbol,
        "interval": interval,
        "outputsize": outputsize,
        "apikey": API_KEY
    }

    try:
        response = requests.get(url, params=params, timeout=15)

        if response.status_code == 200:
            api_manager.record_request()
            data = response.json()

            if "values" in data:
                return data["values"]
            else:
                logger.error(f"خطای API برای {symbol}: {data}")
                return None
        elif response.status_code == 429:
            logger.error("Rate Limit Exceeded!")
            time.sleep(60)
            return None
        else:
            logger.error(f"خطای HTTP: {response.status_code}")
            return None

    except Exception as e:
        logger.error(f"خطا در دریافت داده {symbol}: {e}")
        return None


def analyze_trend(data_5min, symbol_key):
    closes = [float(item["close"]) for item in reversed(data_5min)]
    highs = [float(item["high"]) for item in reversed(data_5min)]
    lows = [float(item["low"]) for item in reversed(data_5min)]

    ema_fast = TechnicalIndicators.calculate_ema(closes, EMA_FAST)
    ema_slow = TechnicalIndicators.calculate_ema(closes, EMA_SLOW)

    adx_result = TechnicalIndicators.calculate_adx(highs, lows, closes, ADX_PERIOD)
    if adx_result:
        adx_values, plus_di, minus_di = adx_result
        current_adx = adx_values[-1] if adx_values else 0
    else:
        current_adx = 0

    if not ema_fast or not ema_slow:
        return None, None, None, None, False

    current_ema_fast = ema_fast[-1]
    current_ema_slow = ema_slow[-1]
    prev_ema_fast = ema_fast[-2] if len(ema_fast) > 1 else current_ema_fast
    prev_ema_slow = ema_slow[-2] if len(ema_slow) > 1 else current_ema_slow

    trend = "NEUTRAL"
    trend_strength = 0

    if current_ema_fast > current_ema_slow and current_adx > ADX_TREND_LEVEL:
        trend = "UP"
        trend_strength = min(100, (current_adx - ADX_TREND_LEVEL) * 2)
    elif current_ema_fast < current_ema_slow and current_adx > ADX_TREND_LEVEL:
        trend = "DOWN"
        trend_strength = min(100, (current_adx - ADX_TREND_LEVEL) * 2)

    reversal = False
    if trend == "UP" and prev_ema_fast <= prev_ema_slow:
        reversal = True
    elif trend == "DOWN" and prev_ema_fast >= prev_ema_slow:
        reversal = True

    is_strong = current_adx > SYMBOL_PARAMS[symbol_key]["STRONG_TREND_ADX"]

    return trend, trend_strength, reversal, current_adx, is_strong


def find_entry_signal(data_1min, trend, symbol_key):
    closes = [float(item["close"]) for item in reversed(data_1min)]
    highs = [float(item["high"]) for item in reversed(data_1min)]
    lows = [float(item["low"]) for item in reversed(data_1min)]

    params = SYMBOL_PARAMS[symbol_key]

    rsi_values = TechnicalIndicators.calculate_rsi(closes, RSI_PERIOD)
    macd_result = TechnicalIndicators.calculate_macd(closes)
    atr_values = TechnicalIndicators.calculate_atr(highs, lows, closes, ATR_PERIOD)

    if not rsi_values or not atr_values or not macd_result[0]:
        return None, None, None, None

    current_rsi = rsi_values[-1]
    current_atr = atr_values[-1]
    current_price = closes[-1]

    macd_line, signal_line, histogram = macd_result
    current_macd = macd_line[-1]
    current_signal = signal_line[-1]
    current_histogram = histogram[-1]
    prev_histogram = histogram[-2] if len(histogram) > 1 else 0

    signal = None
    stop_loss = None
    take_profit = None
    confidence = 0

    if trend == "UP":
        # خرید در پولبک: RSI زیر 50 و MACD صعودی
        if current_rsi < 50 and current_macd > current_signal and current_histogram > prev_histogram:
            signal = "BUY"
            stop_loss = current_price - (current_atr * params['ATR_MULTIPLIER_SL'])
            take_profit = current_price + (current_atr * params['ATR_MULTIPLIER_TP'])
            confidence = min(90, 50 + (50 - current_rsi) * 1.5)
        # برگشت از اشباع فروش
        elif current_rsi > 30 and rsi_values[-2] <= 30:
            signal = "BUY"
            stop_loss = current_price - (current_atr * params['ATR_MULTIPLIER_SL'])
            take_profit = current_price + (current_atr * params['ATR_MULTIPLIER_TP'])
            confidence = 70

    elif trend == "DOWN":
        # فروش در پولبک: RSI بالای 50 و MACD نزولی
        if current_rsi > 50 and current_macd < current_signal and current_histogram < prev_histogram:
            signal = "SELL"
            stop_loss = current_price + (current_atr * params['ATR_MULTIPLIER_SL'])
            take_profit = current_price - (current_atr * params['ATR_MULTIPLIER_TP'])
            confidence = min(90, 50 + (current_rsi - 50) * 1.5)
        # برگشت از اشباع خرید
        elif current_rsi < 70 and rsi_values[-2] >= 70:
            signal = "SELL"
            stop_loss = current_price + (current_atr * params['ATR_MULTIPLIER_SL'])
            take_profit = current_price - (current_atr * params['ATR_MULTIPLIER_TP'])
            confidence = 70

    if confidence < params['MIN_CONFIDENCE']:
        return None, None, None, None

    return signal, stop_loss, take_profit, confidence
def is_market_open(symbol_key):
    now = get_iran_time()

    if symbol_key == "BITCOIN":
        return True

    # بازار طلا (فارکس) - جمعه شب تعطیل، شنبه و یکشنبه تعطیل
    if now.weekday() == 5:  # شنبه
        return False
    if now.weekday() == 6:  # یکشنبه
        return False
    if now.weekday() == 4 and now.hour >= 22:  # جمعه بعد از ۲۲:۰۰ به وقت ایران
        return False
    return True


def process_symbol_trend(api_manager, symbol_key):
    symbol_info = SYMBOLS[symbol_key]

    if not is_market_open(symbol_key):
        return

    data_5min = get_market_data(api_manager, symbol_key, "5min", 100)
    if not data_5min:
        return

    current_price = float(data_5min[0]["close"])
    api_manager.signal_tracker.update_signal_status(symbol_key, current_price)

    trend, trend_strength, reversal, adx, is_strong = analyze_trend(data_5min, symbol_key)

    if trend is None:
        return

    api_manager.trend_state[symbol_key] = {
        'trend': trend,
        'strength': trend_strength,
        'adx': adx,
        'is_strong': is_strong,
        'last_update': get_iran_time().strftime('%H:%M:%S')
    }

    logger.info(f"{symbol_info['name']}: روند {trend} | قدرت {trend_strength:.0f}٪ | ADX {adx:.1f} | قوی: {is_strong}")

    if reversal:
        message = (
            f"🔄 <b>برگشت روند {symbol_info['name']}!</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{symbol_info['emoji']} نماد: {symbol_info['name']}\n"
            f"📉 جهت جدید: {'صعودی 📈' if trend == 'UP' else 'نزولی 📉'}\n"
            f"💰 قیمت: ${current_price:.2f}\n"
            f"📊 ADX: {adx:.1f}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ مراقب تغییر روند باشید\n"
            f"🕐 {get_iran_time().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        send_telegram_message(message)


def process_symbol_signal(api_manager, symbol_key):
    symbol_info = SYMBOLS[symbol_key]
    trend_info = api_manager.trend_state.get(symbol_key, {})

    if not trend_info.get('is_strong', False):
        return

    if trend_info.get('trend') == "NEUTRAL":
        return

    data_1min = get_market_data(api_manager, symbol_key, "1min", 100)
    if not data_1min:
        return

    current_price = float(data_1min[0]["close"])
    api_manager.signal_tracker.update_signal_status(symbol_key, current_price)

    signal, stop_loss, take_profit, confidence = find_entry_signal(
        data_1min,
        trend_info['trend'],
        symbol_key
    )

    if signal and api_manager.should_send_signal(symbol_key, signal):
        signal_data = api_manager.signal_tracker.add_signal(
            symbol_key=symbol_key,
            signal_type=signal,
            entry_price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            confidence=confidence,
            trend=trend_info['trend'],
            trend_strength=trend_info['strength']
        )

        if signal == "BUY":
            risk = stop_loss - current_price
            reward = take_profit - current_price
        else:
            risk = current_price - stop_loss
            reward = current_price - take_profit

        risk_reward = abs(reward / risk) if risk != 0 else 0

        message = (
            f"🎯 <b>سیگنال جدید #{signal_data['id']}</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{symbol_info['emoji']} نماد: {symbol_info['name']}\n"
            f"📊 نوع سیگنال: {signal}\n"
            f"💰 قیمت ورود: ${current_price:.2f}\n"
            f"🛑 حد ضرر: ${stop_loss:.2f}\n"
            f"✅ حد سود: ${take_profit:.2f}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📈 جهت روند: {'صعودی 📈' if trend_info['trend'] == 'UP' else 'نزولی 📉'}\n"
            f"💪 قدرت روند: {trend_info['strength']:.0f}٪\n"
            f"📊 ADX: {trend_info['adx']:.1f}\n"
            f"🎯 اطمینان سیگنال: {confidence:.0f}٪\n"
            f"⚖️ نسبت ریسک/ریوارد: 1:{risk_reward:.2f}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🕐 {get_iran_time().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        send_telegram_message(message)
        logger.info(f"سیگنال #{signal_data['id']} برای {symbol_info['name']} ثبت شد")


def job(api_manager):
    logger.info("🔄 بررسی هوشمند بازار...")

    for symbol_key in SYMBOLS:
        if not SYMBOLS[symbol_key]["enabled"]:
            continue

        try:
            if api_manager.should_check_trend(symbol_key):
                process_symbol_trend(api_manager, symbol_key)
                time.sleep(2)

            if api_manager.should_check_signal(symbol_key):
                process_symbol_signal(api_manager, symbol_key)
                time.sleep(2)

        except Exception as e:
            logger.error(f"خطا در پردازش {symbol_key}: {e}")

    send_daily_report(api_manager)


def send_daily_report(api_manager):
    now = get_iran_time()

    if api_manager.last_report_date == now.strftime('%Y-%m-%d'):
        return

    if now.hour != REPORT_HOUR:
        return

    report = api_manager.signal_tracker.get_daily_report()
    if report:
        message = api_manager.signal_tracker.format_daily_report(report)
        send_telegram_message(message)
        logger.info("گزارش روزانه ارسال شد")
        api_manager.last_report_date = now.strftime('%Y-%m-%d')


def main():
    logger.info("🤖 ربات هوشمند با زمان‌بندی بهینه شروع به کار کرد")

    api_manager = APIManager()

    status = api_manager.get_status()
    active_symbols = [SYMBOLS[key]['name'] for key in SYMBOLS if SYMBOLS[key]['enabled']]

    start_message = (
        "✅ <b>ربات هوشمند فعال شد</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📊 نمادها: {', '.join(active_symbols)}\n"
        f"🎯 استراتژی: MTF هوشمند\n"
        f"⏰ بررسی روند: هر {TREND_CHECK_INTERVAL} دقیقه\n"
        f"⚡ بررسی سیگنال: هر {SIGNAL_CHECK_INTERVAL} دقیقه (در روند قوی)\n"
        f"📈 اندیکاتورها: EMA, RSI, MACD, ADX, ATR\n"
        f"📊 سهمیه API: {status['daily_limit']} درخواست\n"
        f"📋 گزارش روزانه: ساعت {REPORT_HOUR}:00\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🕐 {get_iran_time().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    send_telegram_message(start_message)

    job(api_manager)

    schedule.every(1).minutes.do(job, api_manager=api_manager)

    while True:
        try:
            schedule.run_pending()
            time.sleep(20)

            if api_manager.state.get('date') != get_iran_time().strftime('%Y-%m-%d'):
                logger.info("روز جدید! ریست شمارنده")
                api_manager.state = {'date': get_iran_time().strftime('%Y-%m-%d'), 'requests_today': 0}
                api_manager.last_request_times = []
                api_manager.last_report_date = None
                api_manager.trend_state = {}
                api_manager.last_trend_check = {}
                api_manager.save_state()

        except KeyboardInterrupt:
            logger.info("ربات متوقف شد")
            break
        except Exception as e:
            logger.error(f"خطای غیرمنتظره: {e}")
            time.sleep(60)


if __name__ == "__main__":
    main()