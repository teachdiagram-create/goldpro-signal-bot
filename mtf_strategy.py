from config import MIN_ADX

# =========================================================
# GoldPro MTF Strategy v4
#
# 30M Trend
#     ↓
# 15M Confirmation
#     ↓
# Support / Resistance
#     ↓
# 5M Smart Entry
#
# هدف:
# - از دست ندادن روندهای قوی
# - جلوگیری از ورود نزدیک سقف/کف
# - استفاده از شکست حمایت/مقاومت
# =========================================================


# -----------------------------
# RSI
# -----------------------------

RSI_BUY_MIN = 40
RSI_BUY_MAX = 75

RSI_SELL_MIN = 25
RSI_SELL_MAX = 60


# -----------------------------
# Support / Resistance
# -----------------------------

SR_LOOKBACK = 50

SR_ZONE_ATR = 0.50

BREAKOUT_ATR = 0.20


# -----------------------------
# Strong trend
# -----------------------------

STRONG_ADX = 35


def _latest(df):
    return df.iloc[-1]


# =========================================================
# INDICATORS
# =========================================================

def add_mtf_indicators(df):

    from indicators import add_indicators

    return add_indicators(df.copy())


# =========================================================
# SUPPORT / RESISTANCE
# =========================================================

def _support_resistance(df):

    if df is None or df.empty:
        return None, None

    lookback = min(
        SR_LOOKBACK,
        len(df)
    )

    recent = df.tail(lookback)

    support = float(
        recent["low"].min()
    )

    resistance = float(
        recent["high"].max()
    )

    return support, resistance


# =========================================================
# 30M TREND
# =========================================================

def _trend_30m(df30):

    last = _latest(df30)

    ema20 = float(last["EMA20"])
    ema50 = float(last["EMA50"])
    adx = float(last["ADX"])

    if (
        ema20 > ema50
        and adx >= MIN_ADX
    ):
        return "BUY"

    if (
        ema20 < ema50
        and adx >= MIN_ADX
    ):
        return "SELL"

    return "NONE"


# =========================================================
# 15M CONFIRMATION
# =========================================================

def _confirm_15m(df15, direction):

    last = _latest(df15)

    ema20 = float(last["EMA20"])
    ema50 = float(last["EMA50"])
    adx = float(last["ADX"])

    if direction == "BUY":

        confirmed = (
            ema20 > ema50
            and adx >= MIN_ADX
        )

    else:

        confirmed = (
            ema20 < ema50
            and adx >= MIN_ADX
        )

    return confirmed, {
        "ema20_15": ema20,
        "ema50_15": ema50,
        "adx_15": adx,
        "time_15": str(last["time"])
    }


# =========================================================
# 5M SMART ENTRY
# =========================================================

def _entry_5m(df5, direction):

    last = _latest(df5)

    previous = (
        df5.iloc[-2]
        if len(df5) >= 2
        else None
    )

    price = float(last["close"])

    open_price = float(
        last["open"]
    )

    ema20 = float(
        last["EMA20"]
    )

    ema50 = float(
        last["EMA50"]
    )

    rsi = float(
        last["RSI"]
    )

    adx = float(
        last["ADX"]
    )

    atr = float(
        last["ATR"]
    )

    macd = float(
        last["MACD"]
    )

    macd_signal = float(
        last["MACD_SIGNAL"]
    )

    # =====================================================
    # SUPPORT / RESISTANCE
    # =====================================================

    support, resistance = _support_resistance(
        df5
    )

    distance_to_support = (
        price - support
        if support is not None
        else None
    )

    distance_to_resistance = (
        resistance - price
        if resistance is not None
        else None
    )

    near_support = (
        distance_to_support is not None
        and distance_to_support
        <= atr * SR_ZONE_ATR
    )

    near_resistance = (
        distance_to_resistance is not None
        and distance_to_resistance
        <= atr * SR_ZONE_ATR
    )

    # =====================================================
    # BREAKOUT
    # =====================================================

    breakout_resistance = False
    breakout_support = False

    if previous is not None:

        previous_close = float(
            previous["close"]
        )

        if resistance is not None:

            breakout_resistance = (
                price > resistance
                and previous_close <= resistance
            )

        if support is not None:

            breakout_support = (
                price < support
                and previous_close >= support
            )

    # =====================================================
    # TREND
    # =====================================================

    bullish_trend = (
        ema20 > ema50
    )

    bearish_trend = (
        ema20 < ema50
    )

    # =====================================================
    # MOMENTUM
    # =====================================================

    bullish_momentum = (
        macd >= macd_signal
    )

    bearish_momentum = (
        macd <= macd_signal
    )

    # =====================================================
    # CANDLE
    # =====================================================

    bullish_candle = (
        price > open_price
    )

    bearish_candle = (
        price < open_price
    )

    # =====================================================
    # STRONG TREND
    # =====================================================

    strong_trend = (
        adx >= STRONG_ADX
    )

    # =====================================================
    # RSI
    # =====================================================

    buy_rsi_ok = (
        RSI_BUY_MIN
        <= rsi
        <= RSI_BUY_MAX
    )

    sell_rsi_ok = (
        RSI_SELL_MIN
        <= rsi
        <= RSI_SELL_MAX
    )

    # =====================================================
    # NORMAL ENTRY
    # =====================================================

    if direction == "BUY":

        normal_entry = (
            bullish_trend
            and buy_rsi_ok
            and adx >= MIN_ADX
            and bullish_momentum
            and bullish_candle
        )

    else:

        normal_entry = (
            bearish_trend
            and sell_rsi_ok
            and adx >= MIN_ADX
            and bearish_momentum
            and bearish_candle
        )

    # =====================================================
    # SMART TREND ENTRY
    #
    # در روند قوی، لازم نیست قیمت دقیقاً روی EMA20 باشد.
    # =====================================================

    if direction == "BUY":

        smart_entry = (
            bullish_trend
            and strong_trend
            and rsi <= 75
            and bullish_momentum
            and bullish_candle
        )

    else:

        smart_entry = (
            bearish_trend
            and strong_trend
            and rsi >= 25
            and bearish_momentum
            and bearish_candle
        )

    # =====================================================
    # SUPPORT / RESISTANCE FILTER
    # =====================================================

    sr_ok = True

    sr_reason = "S/R neutral"

    if direction == "BUY":

        # نزدیک مقاومت → ورود خطرناک
        if near_resistance and not breakout_resistance:

            sr_ok = False

            sr_reason = (
                "BUY blocked near resistance"
            )

        # نزدیک حمایت → موقعیت بهتر
        elif near_support:

            sr_reason = (
                "BUY near support"
            )

        # شکست مقاومت
        elif breakout_resistance:

            sr_reason = (
                "BUY resistance breakout"
            )

    else:

        # نزدیک حمایت → ورود خطرناک
        if near_support and not breakout_support:

            sr_ok = False

            sr_reason = (
                "SELL blocked near support"
            )

        # نزدیک مقاومت → موقعیت بهتر
        elif near_resistance:

            sr_reason = (
                "SELL near resistance"
            )

        # شکست حمایت
        elif breakout_support:

            sr_reason = (
                "SELL support breakdown"
            )

    # =====================================================
    # FINAL ENTRY
    # =====================================================

    entry_ready = (
        (normal_entry or smart_entry)
        and sr_ok
    )

    # =====================================================
    # SCORE
    # =====================================================

    score = 0

    reasons = []

    if direction == "BUY":

        if bullish_trend:

            score += 25
            reasons.append(
                "5M bullish trend"
            )

        if buy_rsi_ok:

            score += 15
            reasons.append(
                "RSI acceptable"
            )

        if bullish_momentum:

            score += 20
            reasons.append(
                "MACD bullish"
            )

        if strong_trend:

            score += 15
            reasons.append(
                "Strong 5M trend"
            )

        if bullish_candle:

            score += 10
            reasons.append(
                "Bullish candle"
            )

        if near_support:

            score += 10
            reasons.append(
                "Near support"
            )

        if breakout_resistance:

            score += 15
            reasons.append(
                "Resistance breakout"
            )

    else:

        if bearish_trend:

            score += 25
            reasons.append(
                "5M bearish trend"
            )

        if sell_rsi_ok:

            score += 15
            reasons.append(
                "RSI acceptable"
            )

        if bearish_momentum:

            score += 20
            reasons.append(
                "MACD bearish"
            )

        if strong_trend:

            score += 15
            reasons.append(
                "Strong 5M trend"
            )

        if bearish_candle:

            score += 10
            reasons.append(
                "Bearish candle"
            )

        if near_resistance:

            score += 10
            reasons.append(
                "Near resistance"
            )

        if breakout_support:

            score += 15
            reasons.append(
                "Support breakdown"
            )

    # =====================================================
    # RESULT DATA
    # =====================================================

    return entry_ready, {

        "price": price,

        "rsi": rsi,

        "adx": adx,

        "atr": atr,

        "ema20": ema20,

        "ema50": ema50,

        "macd": macd,

        "macd_signal": macd_signal,

        "support": support,

        "resistance": resistance,

        "distance_to_support": distance_to_support,

        "distance_to_resistance": distance_to_resistance,

        "near_support": near_support,

        "near_resistance": near_resistance,

        "breakout_resistance": breakout_resistance,

        "breakout_support": breakout_support,

        "strong_trend": strong_trend,

        "entry_not_extended": True,

        "sr_reason": sr_reason,

        "score": score,

        "reasons": reasons,

        "time": str(last["time"])
    }


# =========================================================
# MAIN MTF SIGNAL
# =========================================================

def generate_mtf_signal(
    df30,
    df15,
    df5
):

    # =====================================================
    # INDICATORS
    # =====================================================

    df30 = add_mtf_indicators(
        df30
    )

    df15 = add_mtf_indicators(
        df15
    )

    df5 = add_mtf_indicators(
        df5
    )

    # =====================================================
    # 30M TREND
    # =====================================================

    direction = _trend_30m(
        df30
    )

    if direction == "NONE":

        return {

            "signal": "NO SIGNAL",

            "stage": "30M",

            "reasons": [
                "No 30M trend confirmation"
            ]
        }

    # =====================================================
    # 15M CONFIRMATION
    # =====================================================

    confirmed, c = _confirm_15m(
        df15,
        direction
    )

    if not confirmed:

        return {

            "signal": "NO SIGNAL",

            "stage": "15M",

            "trend": direction,

            "reasons": [
                "30M trend confirmed",
                "15M confirmation failed"
            ],

            **c
        }

    # =====================================================
    # 5M ENTRY
    # =====================================================

    entry_ready, e = _entry_5m(
        df5,
        direction
    )

    if not entry_ready:

        return {

            "signal": "NO SIGNAL",

            "stage": "5M",

            "trend": direction,

            "reasons": [
                "30M trend confirmed",
                "15M confirmation confirmed",
                "5M entry not ready",
                e["sr_reason"]
            ],

            **c,
            **e
        }

    # =====================================================
    # FINAL SIGNAL
    # =====================================================

    signal = direction

    score = min(
        100,
        max(
            70,
            e["score"]
        )
    )

    confidence = score

    quality = (
        "STRONG"
        if confidence >= 80
        else "NORMAL"
    )

    # =====================================================
    # SL / TP
    # =====================================================

    if signal == "BUY":

        sl = (
            e["price"]
            - e["atr"] * 1.5
        )

        tp1 = (
            e["price"]
            + e["atr"] * 2
        )

        tp2 = (
            e["price"]
            + e["atr"] * 3
        )

    else:

        sl = (
            e["price"]
            + e["atr"] * 1.5
        )

        tp1 = (
            e["price"]
            - e["atr"] * 2
        )

        tp2 = (
            e["price"]
            - e["atr"] * 3
        )

    # =====================================================
    # REASONS
    # =====================================================

    reasons = [
        "30M trend confirmed",
        "15M confirmation confirmed"
    ]

    reasons.extend(
        e["reasons"]
    )

    reasons.append(
        e["sr_reason"]
    )

    # =====================================================
    # FINAL RESULT
    # =====================================================

    return {

        "signal": signal,

        "score": score,

        "confidence": confidence,

        "quality": quality,

        "reasons": reasons,

        "price": e["price"],

        "sl": sl,

        "tp1": tp1,

        "tp2": tp2,

        "rsi": e["rsi"],

        "adx": e["adx"],

        "atr": e["atr"],

        "support": e["support"],

        "resistance": e["resistance"],

        "distance_to_support":
            e["distance_to_support"],

        "distance_to_resistance":
            e["distance_to_resistance"],

        "stage": "5M",

        "trend": direction
    }