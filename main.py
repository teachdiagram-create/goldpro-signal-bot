import os
import time
import json
import logging
import requests
import schedule
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("GoldProV2")

IRAN_TZ = ZoneInfo("Asia/Tehran")

def now_iran():
    return datetime.now(IRAN_TZ)

# -----------------------------------------------------------------------------
# Environment / Telegram
# -----------------------------------------------------------------------------
API_KEY = os.getenv("TWELVE_DATA_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# -----------------------------------------------------------------------------
# Market configuration
# -----------------------------------------------------------------------------
SYMBOLS = {
    "GOLD": {
        "symbol": "XAU/USD",
        "name": "طلا",
        "emoji": "🥇",
        "enabled": True,
    },
    "BITCOIN": {
        "symbol": "BTC/USD",
        "name": "بیت کوین",
        "emoji": "₿",
        "enabled": False,
    },
}

# GoldPro V2 - Strong Signal
EMA_FAST = 20
EMA_SLOW = 50
RSI_PERIOD = 14
ATR_PERIOD = 14
ADX_PERIOD = 14
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

GOLD = {
    "MIN_ADX": 25.0,
    "VERY_STRONG_ADX": 30.0,
    "MIN_SCORE": 80,
    "MIN_RR": 1.50,
    "SL_ATR_BUFFER": 0.35,
    "MIN_ATR": 0.50,
    "MAX_ATR": 40.0,
    "MAX_ENTRY_DISTANCE_ATR": 0.80,
    "COOLDOWN_MINUTES": 45,
}

# API budget: with 15-minute trend checks and 3-minute entry checks,
# worst case is about 576 data requests/day, below the 680 safe budget.
DAILY_LIMIT = 800
SAFE_MARGIN = 0.85
MINUTE_LIMIT = 8
STATE_FILE = "/tmp/api_state.json"
SIGNALS_FILE = "/tmp/signals_history.json"
REPORT_HOUR = 23
TREND_CHECK_INTERVAL = 15
SIGNAL_CHECK_INTERVAL = 3

# -----------------------------------------------------------------------------
# Telegram
# -----------------------------------------------------------------------------
def send_telegram_message(text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("تنظیمات تلگرام کامل نیست")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code != 200:
            logger.error("خطای تلگرام: %s", response.text)
        return response.status_code == 200
    except Exception as exc:
        logger.error("خطا در ارسال تلگرام: %s", exc)
        return False

# -----------------------------------------------------------------------------
# Technical indicators - no third-party TA dependency
# -----------------------------------------------------------------------------
class TA:
    @staticmethod
    def ema(values, period):
        if len(values) < period:
            return []
        seed = sum(values[:period]) / period
        out = [seed]
        alpha = 2.0 / (period + 1.0)
        for value in values[period:]:
            out.append((value - out[-1]) * alpha + out[-1])
        return out

    @staticmethod
    def rsi(values, period=14):
        if len(values) < period + 1:
            return []
        gains, losses = [], []
        for i in range(1, len(values)):
            change = values[i] - values[i - 1]
            gains.append(max(change, 0.0))
            losses.append(max(-change, 0.0))
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        out = []
        for i in range(period, len(gains)):
            if i > period:
                avg_gain = ((avg_gain * (period - 1)) + gains[i]) / period
                avg_loss = ((avg_loss * (period - 1)) + losses[i]) / period
            if avg_loss == 0:
                out.append(100.0)
            else:
                rs = avg_gain / avg_loss
                out.append(100.0 - (100.0 / (1.0 + rs)))
        return out

    @staticmethod
    def atr(highs, lows, closes, period=14):
        if len(closes) < period + 1:
            return []
        tr = []
        for i in range(1, len(closes)):
            tr.append(max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1])))
        if len(tr) < period:
            return []
        value = sum(tr[:period]) / period
        out = [value]
        for x in tr[period:]:
            value = ((value * (period - 1)) + x) / period
            out.append(value)
        return out

    @staticmethod
    def adx(highs, lows, closes, period=14):
        if len(closes) < period * 2 + 1:
            return None
        tr, plus_dm, minus_dm = [], [], []
        for i in range(1, len(closes)):
            up = highs[i] - highs[i - 1]
            down = lows[i - 1] - lows[i]
            plus_dm.append(up if up > down and up > 0 else 0.0)
            minus_dm.append(down if down > up and down > 0 else 0.0)
            tr.append(max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1])))
        if len(tr) < period * 2:
            return None

        atr = sum(tr[:period]) / period
        p_dm = sum(plus_dm[:period]) / period
        m_dm = sum(minus_dm[:period]) / period
        dx = []
        plus_di_last = minus_di_last = 0.0
        for i in range(period, len(tr)):
            atr = ((atr * (period - 1)) + tr[i]) / period
            p_dm = ((p_dm * (period - 1)) + plus_dm[i]) / period
            m_dm = ((m_dm * (period - 1)) + minus_dm[i]) / period
            pdi = (p_dm / atr) * 100 if atr else 0.0
            mdi = (m_dm / atr) * 100 if atr else 0.0
            plus_di_last, minus_di_last = pdi, mdi
            denom = pdi + mdi
            dx.append(abs(pdi - mdi) / denom * 100 if denom else 0.0)
        if len(dx) < period:
            return None
        adx = sum(dx[:period]) / period
        for value in dx[period:]:
            adx = ((adx * (period - 1)) + value) / period
        return adx, plus_di_last, minus_di_last

    @staticmethod
    def macd(values, fast=12, slow=26, signal=9):
        if len(values) < slow + signal + 5:
            return None
        ef = TA.ema(values, fast)
        es = TA.ema(values, slow)
        n = min(len(ef), len(es))
        macd_line = [ef[-n + i] - es[-n + i] for i in range(n)]
        sig = TA.ema(macd_line, signal)
        if not sig:
            return None
        macd_aligned = macd_line[-len(sig):]
        hist = [m - s for m, s in zip(macd_aligned, sig)]
        return macd_aligned, sig, hist

# -----------------------------------------------------------------------------
# Candle helpers
# -----------------------------------------------------------------------------
def candle_data(rows):
    # Twelve Data returns newest first; reverse into oldest -> newest.
    rows = list(reversed(rows))
    o = [float(x["open"]) for x in rows]
    h = [float(x["high"]) for x in rows]
    l = [float(x["low"]) for x in rows]
    c = [float(x["close"]) for x in rows]
    return o, h, l, c


def bullish_engulfing(o, h, l, c):
    if len(c) < 2:
        return False
    return c[-2] < o[-2] and c[-1] > o[-1] and o[-1] <= c[-2] and c[-1] >= o[-2]


def bearish_engulfing(o, h, l, c):
    if len(c) < 2:
        return False
    return c[-2] > o[-2] and c[-1] < o[-1] and o[-1] >= c[-2] and c[-1] <= o[-2]


def bullish_rejection(o, h, l, c):
    if not c:
        return False
    body = abs(c[-1] - o[-1])
    if body <= 0:
        return False
    lower = min(o[-1], c[-1]) - l[-1]
    upper = h[-1] - max(o[-1], c[-1])
    return lower >= body * 2.0 and upper <= body * 0.75 and c[-1] > o[-1]


def bearish_rejection(o, h, l, c):
    if not c:
        return False
    body = abs(c[-1] - o[-1])
    if body <= 0:
        return False
    upper = h[-1] - max(o[-1], c[-1])
    lower = min(o[-1], c[-1]) - l[-1]
    return upper >= body * 2.0 and lower <= body * 0.75 and c[-1] < o[-1]


def recent_swing_low(lows, lookback=8):
    return min(lows[-lookback:]) if len(lows) >= lookback else min(lows)


def recent_swing_high(highs, lookback=8):
    return max(highs[-lookback:]) if len(highs) >= lookback else max(highs)

# -----------------------------------------------------------------------------
# API manager
# -----------------------------------------------------------------------------
class APIManager:
    def __init__(self):
        self.state = self.load_state()
        self.last_request_times = []
        self.last_trend_check = {}
        self.last_signal_check = {}
        self.last_signal_time = {}
        self.last_report_date = None
        self.trend_state = {}
        self.tracker = SignalTracker()

    def load_state(self):
        today = now_iran().strftime("%Y-%m-%d")
        try:
            with open(STATE_FILE, "r") as f:
                state = json.load(f)
            if state.get("date") == today:
                return state
        except Exception:
            pass
        return {"date": today, "requests_today": 0}

    def save_state(self):
        self.state["date"] = now_iran().strftime("%Y-%m-%d")
        with open(STATE_FILE, "w") as f:
            json.dump(self.state, f)

    def can_request(self):
        now = now_iran()
        if self.state.get("date") != now.strftime("%Y-%m-%d"):
            self.state = {"date": now.strftime("%Y-%m-%d"), "requests_today": 0}
            self.last_request_times = []
            self.save_state()
        effective_daily = int(DAILY_LIMIT * SAFE_MARGIN)
        if self.state.get("requests_today", 0) >= effective_daily:
            logger.warning("سقف امن روزانه API پر شد")
            return False
        self.last_request_times = [t for t in self.last_request_times if (now - t).total_seconds() < 60]
        if len(self.last_request_times) >= MINUTE_LIMIT - 1:
            return False
        return True

    def record_request(self):
        self.last_request_times.append(now_iran())
        self.state["requests_today"] = self.state.get("requests_today", 0) + 1
        self.save_state()

    def due(self, store, key, minutes):
        current = time.time()
        if current - store.get(key, 0) >= minutes * 60:
            store[key] = current
            return True
        return False

    def cooldown_ok(self, symbol_key, signal):
        key = f"{symbol_key}_{signal}"
        last = self.last_signal_time.get(key, 0)
        return time.time() - last >= GOLD["COOLDOWN_MINUTES"] * 60

    def mark_signal(self, symbol_key, signal):
        self.last_signal_time[f"{symbol_key}_{signal}"] = time.time()

# -----------------------------------------------------------------------------
# Signal tracker
# -----------------------------------------------------------------------------
class SignalTracker:
    def __init__(self):
        self.signals = self.load()
        self.counter = self.load_counter()

    def load(self):
        try:
            with open(SIGNALS_FILE, "r") as f:
                data = json.load(f)
            if data.get("date") == now_iran().strftime("%Y-%m-%d"):
                return data.get("signals", [])
        except Exception:
            pass
        return []

    def load_counter(self):
        try:
            with open(SIGNALS_FILE, "r") as f:
                return int(json.load(f).get("total_counter", 0))
        except Exception:
            return 0

    def save(self):
        with open(SIGNALS_FILE, "w") as f:
            json.dump({"date": now_iran().strftime("%Y-%m-%d"), "signals": self.signals, "total_counter": self.counter}, f, indent=2)

    def add(self, symbol_key, signal, entry, sl, tp, confidence, trend, adx, score):
        self.counter += 1
        item = {
            "id": self.counter,
            "symbol": symbol_key,
            "symbol_name": SYMBOLS[symbol_key]["name"],
            "symbol_emoji": SYMBOLS[symbol_key]["emoji"],
            "date": now_iran().strftime("%Y-%m-%d"),
            "time": now_iran().strftime("%H:%M:%S"),
            "type": signal,
            "entry_price": round(entry, 2),
            "stop_loss": round(sl, 2),
            "take_profit": round(tp, 2),
            "confidence": round(confidence, 1),
            "score": score,
            "trend": trend,
            "adx": round(adx, 2),
            "status": "OPEN",
            "result_pips": 0,
            "close_time": None,
            "close_price": None,
        }
        self.signals.append(item)
        self.save()
        return item

    def update(self, symbol_key, price):
        changed = False
        for s in self.signals:
            if s["status"] != "OPEN" or s["symbol"] != symbol_key:
                continue
            entry, sl, tp = s["entry_price"], s["stop_loss"], s["take_profit"]
            hit = None
            if s["type"] == "BUY":
                if price <= sl:
                    hit = "LOSS"
                elif price >= tp:
                    hit = "WIN"
            else:
                if price >= sl:
                    hit = "LOSS"
                elif price <= tp:
                    hit = "WIN"
            if hit:
                s["status"] = hit
                s["close_price"] = round(price, 2)
                s["close_time"] = now_iran().strftime("%H:%M:%S")
                s["result_pips"] = round((price - entry) * 100 if s["type"] == "BUY" else (entry - price) * 100, 2)
                changed = True
                self.close_notification(s)
        if changed:
            self.save()

    def close_notification(self, s):
        emoji = "✅" if s["status"] == "WIN" else "❌"
        msg = (
            f"{emoji} <b>GoldPro V2 — معامله #{s['id']} بسته شد</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{s['symbol_emoji']} {s['symbol_name']} | {s['type']}\n"
            f"💰 ورود: ${s['entry_price']:.2f}\n"
            f"💵 خروج: ${s['close_price']:.2f}\n"
            f"📊 نتیجه: {s['result_pips']:+.2f} پیپ\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🕐 {now_iran().strftime('%H:%M:%S')}"
        )
        send_telegram_message(msg)

    def daily_report(self):
        closed = [s for s in self.signals if s["status"] in ("WIN", "LOSS")]
        wins = [s for s in closed if s["status"] == "WIN"]
        losses = [s for s in closed if s["status"] == "LOSS"]
        wr = len(wins) / len(closed) * 100 if closed else 0
        total = sum(s["result_pips"] for s in closed)
        return (
            f"📊 <b>GoldPro V2 — گزارش روزانه</b>\n"
            f"📅 {now_iran().strftime('%Y-%m-%d')}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🎯 کل سیگنال: {len(self.signals)}\n"
            f"✅ موفق: {len(wins)}\n"
            f"❌ ناموفق: {len(losses)}\n"
            f"⏳ باز: {len(self.signals) - len(closed)}\n"
            f"📈 Win Rate: {wr:.1f}%\n"
            f"💰 مجموع نتیجه: {total:+.2f} پیپ\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🕐 {now_iran().strftime('%H:%M:%S')}"
        )

# -----------------------------------------------------------------------------
# Market data
# -----------------------------------------------------------------------------
def get_market_data(manager, symbol_key, interval, outputsize=120):
    if not API_KEY:
        logger.error("TWELVE_DATA_API_KEY تنظیم نشده است")
        return None
    if not manager.can_request():
        return None
    params = {
        "symbol": SYMBOLS[symbol_key]["symbol"],
        "interval": interval,
        "outputsize": outputsize,
        "apikey": API_KEY,
    }
    try:
        r = requests.get("https://api.twelvedata.com/time_series", params=params, timeout=15)
        if r.status_code == 200:
            data = r.json()
            if "values" in data:
                manager.record_request()
                return data["values"]
            logger.error("خطای Twelve Data: %s", data)
        elif r.status_code == 429:
            logger.warning("Twelve Data rate limit")
        else:
            logger.error("HTTP %s: %s", r.status_code, r.text[:300])
    except Exception as exc:
        logger.error("خطای دریافت داده: %s", exc)
    return None

# -----------------------------------------------------------------------------
# Strong trend: 5-minute closed-candle analysis
# -----------------------------------------------------------------------------
def analyze_trend(rows):
    o, h, l, c = candle_data(rows)
    # Ignore the newest candle because it may still be forming.
    c = c[:-1]; h = h[:-1]; l = l[:-1]
    if len(c) < 80:
        return None

    ef = TA.ema(c, EMA_FAST)
    es = TA.ema(c, EMA_SLOW)
    rsi = TA.rsi(c, RSI_PERIOD)
    adx_data = TA.adx(h, l, c, ADX_PERIOD)
    atr = TA.atr(h, l, c, ATR_PERIOD)
    macd = TA.macd(c, MACD_FAST, MACD_SLOW, MACD_SIGNAL)
    if not all([ef, es, rsi, adx_data, atr, macd]):
        return None

    adx, pdi, mdi = adx_data
    price = c[-1]
    ema20 = ef[-1]
    ema50 = es[-1]
    ema20_prev = ef[-2]
    ema50_prev = es[-2]
    r = rsi[-1]
    hist = macd[2][-1]
    hist_prev = macd[2][-2]

    # V2.1 trend fix:
    # Do not require every condition (price position + both EMA slopes + DI)
    # simultaneously. That combination was too restrictive and could keep a
    # clearly directional market in NEUTRAL. ADX must still confirm trend
    # strength; direction is determined mainly by EMA structure and DI.
    if adx < GOLD["MIN_ADX"]:
        direction = "NEUTRAL"
        trend_reason = f"ADX<{GOLD['MIN_ADX']:.0f}"
    else:
        up_votes = sum([
            price > ema20,
            ema20 > ema50,
            ema20 >= ema20_prev,
            ema50 >= ema50_prev,
            pdi > mdi,
        ])
        down_votes = sum([
            price < ema20,
            ema20 < ema50,
            ema20 <= ema20_prev,
            ema50 <= ema50_prev,
            mdi > pdi,
        ])

        # 3/5 votes is enough for a directional trend, while ADX>=25
        # keeps weak/choppy markets out. In a tie, stay NEUTRAL.
        if up_votes >= 3 and up_votes > down_votes:
            direction = "UP"
            trend_reason = f"UP votes={up_votes}/5"
        elif down_votes >= 3 and down_votes > up_votes:
            direction = "DOWN"
            trend_reason = f"DOWN votes={down_votes}/5"
        else:
            direction = "NEUTRAL"
            trend_reason = f"votes UP={up_votes}/5 DOWN={down_votes}/5"

    logger.info(
        "📐 TREND DEBUG | price=%.2f EMA20=%.2f EMA50=%.2f | ADX=%.1f +DI=%.1f -DI=%.1f | %s | trend=%s",
        price, ema20, ema50, adx, pdi, mdi, trend_reason, direction
    )

    return {
        "trend": direction,
        "adx": adx,
        "pdi": pdi,
        "mdi": mdi,
        "rsi": r,
        "atr": atr[-1],
        "ema20": ema20,
        "ema50": ema50,
        "hist": hist,
        "hist_prev": hist_prev,
        "price": price,
    }

# -----------------------------------------------------------------------------
# Strong entry: 1-minute closed candle + pullback/rejection + scoring
# -----------------------------------------------------------------------------
def find_strong_entry(rows, trend):
    o, h, l, c = candle_data(rows)
    # Work only with completed candles. This is important for avoiding false
    # signals caused by a candle changing shape while it is still open.
    o, h, l, c = o[:-1], h[:-1], l[:-1], c[:-1]
    if len(c) < 80:
        return None

    ef = TA.ema(c, EMA_FAST)
    es = TA.ema(c, EMA_SLOW)
    rsi = TA.rsi(c, RSI_PERIOD)
    atrs = TA.atr(h, l, c, ATR_PERIOD)
    adx_data = TA.adx(h, l, c, ADX_PERIOD)
    macd = TA.macd(c, MACD_FAST, MACD_SLOW, MACD_SIGNAL)
    if not all([ef, es, rsi, atrs, adx_data, macd]):
        return None

    atr = atrs[-1]
    price = c[-1]
    adx, pdi, mdi = adx_data
    r = rsi[-1]
    r_prev = rsi[-2]
    hist = macd[2][-1]
    hist_prev = macd[2][-2]
    ema20, ema50 = ef[-1], es[-1]

    if not (GOLD["MIN_ATR"] <= atr <= GOLD["MAX_ATR"]):
        return None
    if adx < GOLD["MIN_ADX"]:
        return None

    # Avoid chasing an extended move too far away from EMA20.
    distance_atr = abs(price - ema20) / atr if atr else 999
    if distance_atr > GOLD["MAX_ENTRY_DISTANCE_ATR"]:
        return None

    # Pullback means at least one of the recent candles touched/approached EMA20.
    recent_low = min(l[-4:])
    recent_high = max(h[-4:])
    pullback_buy = recent_low <= ema20 + atr * 0.15
    pullback_sell = recent_high >= ema20 - atr * 0.15

    bull_pattern = bullish_engulfing(o, h, l, c) or bullish_rejection(o, h, l, c)
    bear_pattern = bearish_engulfing(o, h, l, c) or bearish_rejection(o, h, l, c)

    # Momentum confirmation: not merely an RSI 50 cross.
    buy_momentum = r > 52 and r > r_prev and hist > 0 and hist >= hist_prev and pdi > mdi
    sell_momentum = r < 48 and r < r_prev and hist < 0 and hist <= hist_prev and mdi > pdi

    # Score is intentionally strict. Signal requires >= 80/100.
    if trend == "UP":
        score = 0
        reasons = []
        if price > ema20 > ema50:
            score += 20; reasons.append("EMA20/50")
        if adx >= GOLD["VERY_STRONG_ADX"]:
            score += 20; reasons.append("ADX30+")
        elif adx >= GOLD["MIN_ADX"]:
            score += 12; reasons.append("ADX25+")
        if pdi > mdi:
            score += 10; reasons.append("+DI")
        if buy_momentum:
            score += 15; reasons.append("Momentum")
        if pullback_buy:
            score += 15; reasons.append("Pullback")
        if bull_pattern:
            score += 15; reasons.append("Candle")
        if 52 <= r <= 68:
            score += 5; reasons.append("RSI zone")
        if score < GOLD["MIN_SCORE"]:
            return None
        signal = "BUY"
        swing = recent_swing_low(l, 10)
        sl = swing - atr * GOLD["SL_ATR_BUFFER"]
        risk = price - sl
        if risk <= 0:
            return None
        tp = price + risk * 1.8

    elif trend == "DOWN":
        score = 0
        reasons = []
        if price < ema20 < ema50:
            score += 20; reasons.append("EMA20/50")
        if adx >= GOLD["VERY_STRONG_ADX"]:
            score += 20; reasons.append("ADX30+")
        elif adx >= GOLD["MIN_ADX"]:
            score += 12; reasons.append("ADX25+")
        if mdi > pdi:
            score += 10; reasons.append("-DI")
        if sell_momentum:
            score += 15; reasons.append("Momentum")
        if pullback_sell:
            score += 15; reasons.append("Pullback")
        if bear_pattern:
            score += 15; reasons.append("Candle")
        if 32 <= r <= 48:
            score += 5; reasons.append("RSI zone")
        if score < GOLD["MIN_SCORE"]:
            return None
        signal = "SELL"
        swing = recent_swing_high(h, 10)
        sl = swing + atr * GOLD["SL_ATR_BUFFER"]
        risk = sl - price
        if risk <= 0:
            return None
        tp = price - risk * 1.8
    else:
        return None

    rr = abs(tp - price) / abs(price - sl)
    if rr < GOLD["MIN_RR"]:
        return None

    confidence = min(99.0, score + min(8.0, max(0.0, adx - 25.0) * 0.8))
    return {
        "signal": signal,
        "entry": price,
        "sl": sl,
        "tp": tp,
        "score": score,
        "confidence": confidence,
        "adx": adx,
        "rsi": r,
        "atr": atr,
        "rr": rr,
        "reasons": reasons,
    }

# -----------------------------------------------------------------------------
# Processing
# -----------------------------------------------------------------------------
def market_open(symbol_key):
    if symbol_key == "BITCOIN":
        return True
    # Forex/gold is normally closed Saturday/Sunday. Friday close approximation
    # retained for the existing bot behaviour.
    n = now_iran()
    if n.weekday() in (5, 6):
        return False
    if n.weekday() == 4 and n.hour >= 22:
        return False
    return True


def update_open_trades(manager, symbol_key):
    rows = get_market_data(manager, symbol_key, "1min", 5)
    if rows:
        manager.tracker.update(symbol_key, float(rows[0]["close"]))


def process_trend(manager, symbol_key):
    if not market_open(symbol_key):
        return
    rows = get_market_data(manager, symbol_key, "5min", 120)
    if not rows:
        return
    trend = analyze_trend(rows)
    if not trend:
        return
    manager.trend_state[symbol_key] = trend
    logger.info("%s | trend=%s ADX=%.1f RSI=%.1f +DI=%.1f -DI=%.1f", SYMBOLS[symbol_key]["name"], trend["trend"], trend["adx"], trend["rsi"], trend["pdi"], trend["mdi"])


def process_signal(manager, symbol_key):
    if not market_open(symbol_key):
        return
    trend = manager.trend_state.get(symbol_key)
    if not trend or trend["trend"] not in ("UP", "DOWN"):
        logger.info("🚫 DEBUG | ورود بررسی نشد: trend موجود نیست یا NEUTRAL است")
        return

    logger.info(
        "🔎 DEBUG | شروع بررسی ورود | trend=%s ADX=%.1f RSI=%.1f +DI=%.1f -DI=%.1f",
        trend["trend"], trend["adx"], trend["rsi"], trend["pdi"], trend["mdi"]
    )

    rows = get_market_data(manager, symbol_key, "1min", 120)
    if not rows:
        return
    manager.tracker.update(symbol_key, float(rows[0]["close"]))

    result = find_strong_entry(rows, trend["trend"])
    if not result:
        return
    if not manager.cooldown_ok(symbol_key, result["signal"]):
        return

    data = manager.tracker.add(symbol_key, result["signal"], result["entry"], result["sl"], result["tp"], result["confidence"], trend["trend"], result["adx"], result["score"])
    manager.mark_signal(symbol_key, result["signal"])

    direction = "صعودی 📈" if result["signal"] == "BUY" else "نزولی 📉"
    msg = (
        f"🔥 <b>GOLDPRO V2 — STRONG SIGNAL #{data['id']}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🥇 نماد: {SYMBOLS[symbol_key]['name']} (XAU/USD)\n"
        f"📊 سیگنال: <b>{result['signal']}</b>\n"
        f"💰 ورود: ${result['entry']:.2f}\n"
        f"🛑 SL: ${result['sl']:.2f}\n"
        f"🎯 TP: ${result['tp']:.2f}\n"
        f"⚖️ R/R: 1:{result['rr']:.2f}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📈 روند 5M: {direction}\n"
        f"💪 ADX: {result['adx']:.1f}\n"
        f"📊 RSI: {result['rsi']:.1f}\n"
        f"⭐ Score: {result['score']}/100\n"
        f"🎯 Confidence: {result['confidence']:.0f}%\n"
        f"🔎 تأیید: {', '.join(result['reasons'])}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"⏱️ Strategy: Pullback + Momentum + Structure\n"
        f"🕐 {now_iran().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    send_telegram_message(msg)
    logger.info("🔥 STRONG %s #%s | score=%s confidence=%.0f", result["signal"], data["id"], result["score"], result["confidence"])


def daily_report(manager):
    today = now_iran().strftime("%Y-%m-%d")
    if manager.last_report_date == today or now_iran().hour != REPORT_HOUR:
        return
    if manager.tracker.signals:
        send_telegram_message(manager.tracker.daily_report())
        manager.last_report_date = today


def job(manager):
    logger.info("🔄 GoldPro V2 بررسی بازار")
    for key, info in SYMBOLS.items():
        if not info["enabled"]:
            continue
        try:
            # Update the 5M trend before the first 1M entry check.
            # This prevents the startup cycle from being skipped because
            # trend_state has not been initialized yet.
            if manager.due(manager.last_trend_check, key, TREND_CHECK_INTERVAL):
                process_trend(manager, key)
            if manager.due(manager.last_signal_check, key, SIGNAL_CHECK_INTERVAL):
                process_signal(manager, key)
        except Exception as exc:
            logger.exception("خطا در پردازش %s: %s", key, exc)
    daily_report(manager)


def main():
    logger.info("🔥 GoldPro V2 Strong Signal شروع شد")
    if not API_KEY:
        logger.error("TWELVE_DATA_API_KEY پیدا نشد")
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("متغیرهای تلگرام کامل نیستند")

    manager = APIManager()
    startup = (
        "🔥 <b>GoldPro V2 — Strong Signal فعال شد</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🥇 نماد: XAU/USD\n"
        "🧭 روند: 5M | ورود: 1M\n"
        "📈 EMA: 20/50\n"
        "💪 حداقل ADX: 25\n"
        "⭐ حداقل Score: 80/100\n"
        "🎯 حداقل R/R: 1:1.5\n"
        "🧲 ورود: Pullback + Momentum + Candle\n"
        "🛡️ SL: Swing + ATR Buffer\n"
        "⏱️ روند هر 15 دقیقه | ورود هر 3 دقیقه\n"
        "⚠️ فقط سیگنال‌های قوی؛ بدون معامله خودکار\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🕐 {now_iran().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    send_telegram_message(startup)
    job(manager)
    schedule.every(1).minutes.do(job, manager=manager)

    while True:
        try:
            schedule.run_pending()
            time.sleep(10)
            if manager.state.get("date") != now_iran().strftime("%Y-%m-%d"):
                manager.state = {"date": now_iran().strftime("%Y-%m-%d"), "requests_today": 0}
                manager.last_request_times = []
                manager.last_report_date = None
                manager.last_trend_check = {}
                manager.last_signal_check = {}
                manager.trend_state = {}
                manager.save_state()
                manager.tracker.signals = []
        except KeyboardInterrupt:
            logger.info("ربات متوقف شد")
            break
        except Exception as exc:
            logger.exception("خطای اصلی: %s", exc)
            time.sleep(30)


if __name__ == "__main__":
    main()
