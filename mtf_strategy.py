from config import MIN_ADX

# =========================================================
# GoldPro MTF Early Entry Strategy
# 15M Trend → 5M Early Entry → 1M Trigger
# =========================================================

RSI_BUY_MIN = 38
RSI_BUY_MAX = 65

RSI_SELL_MIN = 35
RSI_SELL_MAX = 62

MIN_TREND_ADX = 25

# فاصله مجاز قیمت از EMA20 بر اساس ATR
NORMAL_ENTRY_ATR = 1.50
EARLY_ENTRY_ATR = 2.50


def _latest(df):
    return df.iloc[-1]


def add_mtf_indicators(df):
    from indicators import add_indicators
    return add_indicators(df.copy())


# =========================================================
# 15M TREND
# =========================================================

def _trend_15m(df15):

    last = _latest(df15)

    ema20 = float(last["EMA20"])
    ema50 = float(last["EMA50"])
    adx = float(last["ADX"])

    if ema20 > ema50 and adx >= MIN_TREND_ADX:
        return "BUY"

    if ema20 < ema50 and adx >= MIN_TREND_ADX:
        return "SELL"

    return "NONE"


# =========================================================
# 5M EARLY ENTRY
# =========================================================

def _setup_5m(df5, direction):

    last = _latest(df5)

    prev = df5.iloc[-2] if len(df5) >= 2 else None

    price = float(last["close"])
    ema20 = float(last["EMA20"])
    ema50 = float(last["EMA50"])

    rsi = float(last["RSI"])
    adx = float(last["ADX"])
    atr = float(last["ATR"])

    macd = float(last["MACD"])
    macd_signal = float(last["MACD_SIGNAL"])

    distance_from_ema = abs(price - ema20)

    # -----------------------------------------------------
    # Momentum
    # -----------------------------------------------------

    macd_bullish = macd >= macd_signal
    macd_bearish = macd <= macd_signal

    previous_macd = None
    previous_signal = None

    if prev is not None:
        previous_macd = float(prev["MACD"])
        previous_signal = float(prev["MACD_SIGNAL"])

    # =====================================================
    # BUY
    # =====================================================

    if direction == "BUY":

        trend_ok = ema20 > ema50

        # RSI نباید بیش از حد بالا باشد
        rsi_ok = RSI_BUY_MIN <= rsi <= RSI_BUY_MAX

        # ورود عادی
        normal_entry = (
            distance_from_ema <= atr * NORMAL_ENTRY_ATR
        )

        # ورود زودتر در روند قوی
        early_entry = (
            distance_from_ema <= atr * EARLY_ENTRY_ATR
            and adx >= 30
            and rsi >= 40
            and rsi <= 60
        )

        momentum_ok = (
            macd_bullish
            or (
                previous_macd is not None
                and macd > previous_macd
            )
        )

        setup = (
            trend_ok
            and rsi_ok
            and adx >= MIN_TREND_ADX
            and momentum_ok
            and (
                normal_entry
                or early_entry
            )
        )

        entry_type = (
            "NORMAL"
            if normal_entry
            else "EARLY"
            if early_entry
            else "NONE"
        )

    # =====================================================
    # SELL
    # =====================================================

    else:

        trend_ok = ema20 < ema50

        # RSI برای SELL
        rsi_ok = RSI_SELL_MIN <= rsi <= RSI_SELL_MAX

        # ورود عادی
        normal_entry = (
            distance_from_ema <= atr * NORMAL_ENTRY_ATR
        )

        # -------------------------------------------------
        # EARLY SELL
        #
        # اجازه ورود کمی دورتر از EMA20
        # ولی فقط در روند بسیار قوی
        # -------------------------------------------------

        early_entry = (
            distance_from_ema <= atr * EARLY_ENTRY_ATR
            and adx >= 30
            and rsi >= 35
            and rsi <= 55
            and macd_bearish
        )

        # -------------------------------------------------
        # اگر RSI خیلی پایین باشد، دنبال قیمت نمی‌رویم
        # -------------------------------------------------

        oversold_protection = (
            rsi < 30
            and not normal_entry
        )

        momentum_ok = (
            macd_bearish
            or (
                previous_macd is not None
                and macd < previous_macd
            )
        )

        setup = (
            trend_ok
            and rsi_ok
            and adx >= MIN_TREND_ADX
            and momentum_ok
            and (
                normal_entry
                or early_entry
            )
            and not oversold_protection
        )

        entry_type = (
            "NORMAL"
            if normal_entry
            else "EARLY"
            if early_entry
            else "NONE"
        )

    # =====================================================
    # RESULT
    # =====================================================

    return setup, {
        "price": price,
        "rsi": rsi,
        "adx": adx,
        "atr": atr,

        "ema20": ema20,
        "ema50": ema50,

        "macd": macd,
        "macd_signal": macd_signal,

        "time": str(last["time"]),

        "distance_from_ema": distance_from_ema,

        "entry_type": entry_type,

        "entry_not_extended": (
            distance_from_ema <= atr * EARLY_ENTRY_ATR
        )
    }


# =========================================================
# 1M TRIGGER
# =========================================================

def _trigger_1m(df1, direction):

    if df1 is None or len(df1) < 3:
        return False, "Not enough 1M candles"

    last = _latest(df1)
    prev = df1.iloc[-2]

    close = float(last["close"])
    open_ = float(last["open"])

    prev_close = float(prev["close"])

    ema = float(last["EMA20"])

    rsi = float(last["RSI"])

    macd = float(last["MACD"])
    macd_sig = float(last["MACD_SIGNAL"])

    # =====================================================
    # BUY
    # =====================================================

    if direction == "BUY":

        bullish_candle = close > open_
        price_confirmation = close > prev_close
        ema_confirmation = close >= ema
        rsi_confirmation = rsi >= 43
        macd_confirmation = macd >= macd_sig

        trigger = (
            bullish_candle
            and price_confirmation
            and ema_confirmation
            and rsi_confirmation
            and macd_confirmation
        )

        if trigger:
            return True, "1M bullish trigger"

        return False, "Waiting for 1M bullish trigger"

    # =====================================================
    # SELL
    # =====================================================

    bearish_candle = close < open_
    price_confirmation = close < prev_close
    ema_confirmation = close <= ema
    rsi_confirmation = rsi <= 57
    macd_confirmation = macd <= macd_sig

    trigger = (
        bearish_candle
        and price_confirmation
        and ema_confirmation
        and rsi_confirmation
        and macd_confirmation
    )

    if trigger:
        return True, "1M bearish trigger"

    return False, "Waiting for 1M bearish trigger"


# =========================================================
# MAIN MTF SIGNAL
# =========================================================

def generate_mtf_signal(df15, df5, df1=None):

    df15 = add_mtf_indicators(df15)
    df5 = add_mtf_indicators(df5)

    if df1 is not None:
        df1 = add_mtf_indicators(df1)

    # =====================================================
    # 15M TREND
    # =====================================================

    direction = _trend_15m(df15)

    if direction == "NONE":

        return {
            "signal": "NO SIGNAL",
            "stage": "15M",
            "reasons": [
                "No 15M trend confirmation"
            ]
        }

    # =====================================================
    # 5M SETUP
    # =====================================================

    setup, s = _setup_5m(
        df5,
        direction
    )

    if not setup:

        reason = "No 5M early-entry setup"

        if s["rsi"] < 30 and direction == "SELL":
            reason = "SELL protected: RSI oversold"

        elif s["distance_from_ema"] > s["atr"] * EARLY_ENTRY_ATR:
            reason = "5M price too far from EMA20"

        return {
            "signal": "NO SIGNAL",
            "stage": "5M",
            "trend": direction,
            "reasons": [
                "15M trend confirmed",
                reason
            ],
            **s
        }

    # =====================================================
    # 5M READY → 1M
    # =====================================================

    if df1 is None:

        return {
            "signal": "NO SIGNAL",
            "stage": "1M",
            "trend": direction,
            "reasons": [
                "15M trend confirmed",
                f"5M {s['entry_type']} entry setup ready",
                "Waiting for 1M trigger"
            ],
            **s
        }

    # =====================================================
    # 1M TRIGGER
    # =====================================================

    trigger, trigger_reason = _trigger_1m(
        df1,
        direction
    )

    if not trigger:

        return {
            "signal": "NO SIGNAL",
            "stage": "1M",
            "trend": direction,
            "reasons": [
                "15M trend confirmed",
                f"5M {s['entry_type']} entry setup ready",
                trigger_reason
            ],
            **s
        }

    # =====================================================
    # FINAL SIGNAL
    # =====================================================

    score = 80
    confidence = 80
    quality = "STRONG"

    signal = direction

    if direction == "BUY":

        sl = (
            s["price"]
            - s["atr"] * 1.5
        )

        tp1 = (
            s["price"]
            + s["atr"] * 2
        )

        tp2 = (
            s["price"]
            + s["atr"] * 3
        )

    else:

        sl = (
            s["price"]
            + s["atr"] * 1.5
        )

        tp1 = (
            s["price"]
            - s["atr"] * 2
        )

        tp2 = (
            s["price"]
            - s["atr"] * 3
        )

    return {

        "signal": signal,

        "score": score,

        "confidence": confidence,

        "quality": quality,

        "reasons": [
            "15M trend confirmed",
            f"5M {s['entry_type']} entry",
            trigger_reason
        ],

        "price": s["price"],

        "sl": sl,

        "tp1": tp1,

        "tp2": tp2,

        "rsi": s["rsi"],

        "adx": s["adx"],

        "atr": s["atr"],

        "stage": "1M",

        "trend": direction,

        "entry_type": s["entry_type"]
    }