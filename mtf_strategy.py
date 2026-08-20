# =========================================================
# GoldPro MTF Strategy V5 - Clean Version
#
# BUY:
# 1. EMA20 > EMA50 on 15M -> bullish trend
# 2. RSI went below 30 and crossed back above 30 on 5M
# 3. Last 5M candle is bullish
# 4. Last 5M close > previous 5M close
# 5. Price is near 5M or 15M support
# 6. Bullish RSI divergence = bonus
#
# SELL:
# 1. EMA20 < EMA50 on 15M -> bearish trend
# 2. RSI went above 70 and crossed back below 70 on 5M
# 3. Last 5M candle is bearish
# 4. Last 5M close < previous 5M close
# 5. Price is near 5M or 15M resistance
# 6. Bearish RSI divergence = bonus
#
# EMA20 / EMA50 ONLY define trend.
#
# Minimum signal score = 70
# =========================================================

from indicators import add_indicators


# =========================================================
# SETTINGS
# =========================================================

MIN_SCORE = 70

RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70

SR_LOOKBACK_5M = 20
SR_LOOKBACK_15M = 20

SR_ATR_DISTANCE = 1.0

SL_ATR_MULTIPLIER = 1.5
TP1_ATR_MULTIPLIER = 2.0
TP2_ATR_MULTIPLIER = 3.0


# =========================================================
# BASIC HELPERS
# =========================================================

def _safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def _latest(df):
    return df.iloc[-1]


def _previous(df):
    return df.iloc[-2]


def _prepare(df):
    if df is None or df.empty:
        return None

    try:
        return add_indicators(df.copy())
    except Exception as e:
        print("Indicator error:", e)
        return None


# =========================================================
# TREND
# EMA20 / EMA50 ONLY
# =========================================================

def _get_trend_15m(df15):
    if df15 is None or len(df15) < 2:
        return "NONE"

    last = _latest(df15)

    ema20 = _safe_float(last.get("EMA20"))
    ema50 = _safe_float(last.get("EMA50"))

    if ema20 > ema50:
        return "BUY"

    if ema20 < ema50:
        return "SELL"

    return "NONE"


# =========================================================
# RSI BUY REVERSAL
#
# RSI:
# below 30 -> back above 30
# =========================================================

def _rsi_buy_trigger(df5):
    if df5 is None or len(df5) < 3:
        return False

    current = _safe_float(df5.iloc[-1]["RSI"])
    previous = _safe_float(df5.iloc[-2]["RSI"])
    before = _safe_float(df5.iloc[-3]["RSI"])

    went_oversold = (
        before < RSI_OVERSOLD
        or previous < RSI_OVERSOLD
    )

    crossed_back = (
        previous <= RSI_OVERSOLD
        and current > RSI_OVERSOLD
    )

    return went_oversold and crossed_back


# =========================================================
# RSI SELL REVERSAL
#
# RSI:
# above 70 -> back below 70
# =========================================================

def _rsi_sell_trigger(df5):
    if df5 is None or len(df5) < 3:
        return False

    current = _safe_float(df5.iloc[-1]["RSI"])
    previous = _safe_float(df5.iloc[-2]["RSI"])
    before = _safe_float(df5.iloc[-3]["RSI"])

    went_overbought = (
        before > RSI_OVERBOUGHT
        or previous > RSI_OVERBOUGHT
    )

    crossed_back = (
        previous >= RSI_OVERBOUGHT
        and current < RSI_OVERBOUGHT
    )

    return went_overbought and crossed_back


# =========================================================
# CANDLE CONFIRMATION
# =========================================================

def _bullish_candle(df5):
    if df5 is None or len(df5) < 2:
        return False

    last = _latest(df5)
    prev = _previous(df5)

    open_price = _safe_float(last["open"])
    close = _safe_float(last["close"])
    prev_close = _safe_float(prev["close"])

    return (
        close > open_price
        and close > prev_close
    )


def _bearish_candle(df5):
    if df5 is None or len(df5) < 2:
        return False

    last = _latest(df5)
    prev = _previous(df5)

    open_price = _safe_float(last["open"])
    close = _safe_float(last["close"])
    prev_close = _safe_float(prev["close"])

    return (
        close < open_price
        and close < prev_close
    )


# =========================================================
# SUPPORT
# =========================================================

def _find_support(df, lookback):
    if df is None or df.empty:
        return None

    if len(df) < lookback:
        lookback = len(df)

    if lookback <= 0:
        return None

    recent = df.iloc[-lookback:]

    return _safe_float(recent["low"].min(), None)


# =========================================================
# RESISTANCE
# =========================================================

def _find_resistance(df, lookback):
    if df is None or df.empty:
        return None

    if len(df) < lookback:
        lookback = len(df)

    if lookback <= 0:
        return None

    recent = df.iloc[-lookback:]

    return _safe_float(recent["high"].max(), None)


# =========================================================
# SUPPORT CONTEXT
# =========================================================

def _support_context(df5, df15):
    price = _safe_float(_latest(df5)["close"])
    atr = _safe_float(_latest(df5)["ATR"])

    support5 = _find_support(
        df5,
        SR_LOOKBACK_5M
    )

    support15 = _find_support(
        df15,
        SR_LOOKBACK_15M
    )

    max_distance = max(
        atr * SR_ATR_DISTANCE,
        0.5
    )

    distance5 = (
        abs(price - support5)
        if support5 is not None
        else float("inf")
    )

    distance15 = (
        abs(price - support15)
        if support15 is not None
        else float("inf")
    )

    near5 = distance5 <= max_distance
    near15 = distance15 <= max_distance

    confirmed = near5 or near15

    return confirmed, {
        "support_5m": support5,
        "support_15m": support15,
        "distance_to_support_5m": distance5,
        "distance_to_support_15m": distance15,
        "near_support_5m": near5,
        "near_support_15m": near15
    }


# =========================================================
# RESISTANCE CONTEXT
# =========================================================

def _resistance_context(df5, df15):
    price = _safe_float(_latest(df5)["close"])
    atr = _safe_float(_latest(df5)["ATR"])

    resistance5 = _find_resistance(
        df5,
        SR_LOOKBACK_5M
    )

    resistance15 = _find_resistance(
        df15,
        SR_LOOKBACK_15M
    )

    max_distance = max(
        atr * SR_ATR_DISTANCE,
        0.5
    )

    distance5 = (
        abs(price - resistance5)
        if resistance5 is not None
        else float("inf")
    )

    distance15 = (
        abs(price - resistance15)
        if resistance15 is not None
        else float("inf")
    )

    near5 = distance5 <= max_distance
    near15 = distance15 <= max_distance

    confirmed = near5 or near15

    return confirmed, {
        "resistance_5m": resistance5,
        "resistance_15m": resistance15,
        "distance_to_resistance_5m": distance5,
        "distance_to_resistance_15m": distance15,
        "near_resistance_5m": near5,
        "near_resistance_15m": near15
    }


# =========================================================
# BULLISH RSI DIVERGENCE
# =========================================================

def _bullish_divergence(df5):
    if df5 is None or len(df5) < 10:
        return False

    recent = df5.iloc[-10:]

    first = recent.iloc[:5]
    second = recent.iloc[5:]

    price_low_1 = _safe_float(
        first["low"].min()
    )

    price_low_2 = _safe_float(
        second["low"].min()
    )

    idx1 = first["low"].idxmin()
    idx2 = second["low"].idxmin()

    rsi_low_1 = _safe_float(
        first.loc[idx1, "RSI"]
    )

    rsi_low_2 = _safe_float(
        second.loc[idx2, "RSI"]
    )

    return (
        price_low_2 < price_low_1
        and rsi_low_2 > rsi_low_1
    )


# =========================================================
# BEARISH RSI DIVERGENCE
# =========================================================

def _bearish_divergence(df5):
    if df5 is None or len(df5) < 10:
        return False

    recent = df5.iloc[-10:]

    first = recent.iloc[:5]
    second = recent.iloc[5:]

    price_high_1 = _safe_float(
        first["high"].max()
    )

    price_high_2 = _safe_float(
        second["high"].max()
    )

    idx1 = first["high"].idxmax()
    idx2 = second["high"].idxmax()

    rsi_high_1 = _safe_float(
        first.loc[idx1, "RSI"]
    )

    rsi_high_2 = _safe_float(
        second.loc[idx2, "RSI"]
    )

    return (
        price_high_2 > price_high_1
        and rsi_high_2 < rsi_high_1
    )


# =========================================================
# BUY ANALYSIS
#
# Score:
#
# Trend       = 20
# RSI         = 35
# Candle      = 20
# Support     = 15
# Divergence  = +10
#
# Maximum = 100
# =========================================================

def _analyze_buy(df15, df5):
    trend = _get_trend_15m(df15)

    rsi_trigger = _rsi_buy_trigger(df5)

    candle_ok = _bullish_candle(df5)

    support_ok, sr = _support_context(
        df5,
        df15
    )

    divergence = _bullish_divergence(df5)

    score = 0

    reasons = []

    filters = {}

    # Trend
    filters["Trend"] = trend == "BUY"

    if filters["Trend"]:
        score += 20
        reasons.append(
            "OK: EMA20 > EMA50 bullish trend"
        )
    else:
        reasons.append(
            "WAIT: bullish EMA trend"
        )

    # RSI
    filters["RSI Reversal"] = rsi_trigger

    if rsi_trigger:
        score += 35
        reasons.append(
            "OK: RSI below 30 -> crossed back above 30"
        )
    else:
        reasons.append(
            "WAIT: RSI reversal"
        )

    # Candle
    filters["5M Candle"] = candle_ok

    if candle_ok:
        score += 20
        reasons.append(
            "OK: bullish 5M candle"
        )
    else:
        reasons.append(
            "WAIT: bullish 5M candle"
        )

    # Support
    filters["Support"] = support_ok

    if support_ok:
        score += 15
        reasons.append(
            "OK: price near 5M/15M support"
        )
    else:
        reasons.append(
            "WAIT: 5M/15M support"
        )

    # Divergence bonus
    if divergence:
        score += 10
        reasons.append(
            "BONUS: bullish RSI divergence"
        )
    else:
        reasons.append(
            "No bullish RSI divergence"
        )

    return (
        score,
        filters,
        reasons,
        sr,
        divergence
    )


# =========================================================
# SELL ANALYSIS
#
# Score:
#
# Trend       = 20
# RSI         = 35
# Candle      = 20
# Resistance  = 15
# Divergence  = +10
#
# Maximum = 100
# =========================================================

def _analyze_sell(df15, df5):
    trend = _get_trend_15m(df15)

    rsi_trigger = _rsi_sell_trigger(df5)

    candle_ok = _bearish_candle(df5)

    resistance_ok, sr = _resistance_context(
        df5,
        df15
    )

    divergence = _bearish_divergence(df5)

    score = 0

    reasons = []

    filters = {}

    # Trend
    filters["Trend"] = trend == "SELL"

    if filters["Trend"]:
        score += 20
        reasons.append(
            "OK: EMA20 < EMA50 bearish trend"
        )
    else:
        reasons.append(
            "WAIT: bearish EMA trend"
        )

    # RSI
    filters["RSI Reversal"] = rsi_trigger

    if rsi_trigger:
        score += 35
        reasons.append(
            "OK: RSI above 70 -> crossed back below 70"
        )
    else:
        reasons.append(
            "WAIT: RSI reversal"
        )

    # Candle
    filters["5M Candle"] = candle_ok

    if candle_ok:
        score += 20
        reasons.append(
            "OK: bearish 5M candle"
        )
    else:
        reasons.append(
            "WAIT: bearish 5M candle"
        )

    # Resistance
    filters["Resistance"] = resistance_ok

    if resistance_ok:
        score += 15
        reasons.append(
            "OK: price near 5M/15M resistance"
        )
    else:
        reasons.append(
            "WAIT: 5M/15M resistance"
        )

    # Divergence bonus
    if divergence:
        score += 10
        reasons.append(
            "BONUS: bearish RSI divergence"
        )
    else:
        reasons.append(
            "No bearish RSI divergence"
        )

    return (
        score,
        filters,
        reasons,
        sr,
        divergence
    )


# =========================================================
# SIGNAL RESULT BUILDER
# =========================================================

def _build_signal(
    signal,
    score,
    trend,
    price,
    atr,
    rsi,
    adx,
    ema20,
    ema50,
    macd,
    macd_signal,
    sr,
    divergence,
    filters,
    reasons,
    candle_time
):
    if signal == "BUY":
        sl = price - (
            atr * SL_ATR_MULTIPLIER
        )

        tp1 = price + (
            atr * TP1_ATR_MULTIPLIER
        )

        tp2 = price + (
            atr * TP2_ATR_MULTIPLIER
        )

    else:
        sl = price + (
            atr * SL_ATR_MULTIPLIER
        )

        tp1 = price - (
            atr * TP1_ATR_MULTIPLIER
        )

        tp2 = price - (
            atr * TP2_ATR_MULTIPLIER
        )

    if score >= 85:
        quality = "STRONG"
    elif score >= 70:
        quality = "NORMAL"
    else:
        quality = "WEAK"

    final_reasons = [
        f"Score: {score}/100"
    ]

    final_reasons.extend(reasons)

    final_reasons.append(
        f"FINAL {signal} SIGNAL"
    )

    return {
        "signal": signal,
        "score": score,
        "confidence": score,
        "quality": quality,
        "stage": "5M",
        "trend": trend,
        "price": price,
        "sl": sl,
        "tp1": tp1,
        "tp2": tp2,
        "rsi": rsi,
        "adx": adx,
        "atr": atr,
        "ema20": ema20,
        "ema50": ema50,
        "macd": macd,
        "macd_signal": macd_signal,
        "support": sr.get("support_5m"),
        "support_15m": sr.get("support_15m"),
        "resistance": sr.get("resistance_5m"),
        "resistance_15m": sr.get("resistance_15m"),
        "divergence": divergence,
        "filters": filters,
        "reasons": final_reasons,
        "time": str(candle_time)
    }


# =========================================================
# NO SIGNAL RESULT
# =========================================================

def _build_no_signal(
    trend,
    score,
    price,
    rsi,
    adx,
    atr,
    ema20,
    ema50,
    macd,
    macd_signal,
    sr,
    divergence,
    filters,
    reasons,
    candle_time
):
    if score >= 85:
        quality = "STRONG"
    elif score >= 70:
        quality = "NORMAL"
    else:
        quality = "WEAK"

    return {
        "signal": "NO SIGNAL",
        "stage": "5M",
        "trend": trend,
        "score": score,
        "confidence": score,
        "quality": quality,
        "price": price,
        "rsi": rsi,
        "adx": adx,
        "atr": atr,
        "ema20": ema20,
        "ema50": ema50,
        "macd": macd,
        "macd_signal": macd_signal,
        "support": sr.get("support_5m"),
        "support_15m": sr.get("support_15m"),
        "resistance": sr.get("resistance_5m"),
        "resistance_15m": sr.get("resistance_15m"),
        "divergence": divergence,
        "filters": filters,
        "reasons": [
            f"Score: {score}/100"
        ] + reasons,
        "time": str(candle_time)
    }


# =========================================================
# MAIN
# =========================================================

def generate_mtf_signal(df30, df15, df5):

    if (
        df30 is None
        or df15 is None
        or df5 is None
        or df30.empty
        or df15.empty
        or df5.empty
    ):
        return {
            "signal": "NO SIGNAL",
            "stage": "DATA",
            "score": 0,
            "confidence": 0,
            "quality": "WEAK",
            "reasons": [
                "Insufficient market data"
            ]
        }

    # Prepare indicators
    df30 = _prepare(df30)
    df15 = _prepare(df15)
    df5 = _prepare(df5)

    if (
        df30 is None
        or df15 is None
        or df5 is None
    ):
        return {
            "signal": "NO SIGNAL",
            "stage": "DATA",
            "score": 0,
            "confidence": 0,
            "quality": "WEAK",
            "reasons": [
                "Indicator calculation failed"
            ]
        }

    if len(df15) < 2 or len(df5) < 10:
        return {
            "signal": "NO SIGNAL",
            "stage": "DATA",
            "score": 0,
            "confidence": 0,
            "quality": "WEAK",
            "reasons": [
                "Not enough candles"
            ]
        }

    # -----------------------------------------------------
    # Current market values
    # -----------------------------------------------------

    last = _latest(df5)

    price = _safe_float(
        last["close"]
    )

    rsi = _safe_float(
        last["RSI"]
    )

    atr = _safe_float(
        last["ATR"]
    )

    ema20 = _safe_float(
        last["EMA20"]
    )

    ema50 = _safe_float(
        last["EMA50"]
    )

    macd = _safe_float(
        last["MACD"]
    )

    macd_signal = _safe_float(
        last["MACD_SIGNAL"]
    )

    adx = _safe_float(
        last["ADX"]
    )

    candle_time = last["time"]

    # -----------------------------------------------------
    # Trend
    # -----------------------------------------------------

    trend = _get_trend_15m(df15)

    # -----------------------------------------------------
    # BUY
    # -----------------------------------------------------

    if trend == "BUY":

        (
            score,
            filters,
            reasons,
            sr,
            divergence
        ) = _analyze_buy(
            df15,
            df5
        )

        if score >= MIN_SCORE:
            return _build_signal(
                "BUY",
                score,
                trend,
                price,
                atr,
                rsi,
                adx,
                ema20,
                ema50,
                macd,
                macd_signal,
                sr,
                divergence,
                filters,
                reasons,
                candle_time
            )

        return _build_no_signal(
            trend,
            score,
            price,
            rsi,
            adx,
            atr,
            ema20,
            ema50,
            macd,
            macd_signal,
            sr,
            divergence,
            filters,
            reasons,
            candle_time
        )

    # -----------------------------------------------------
    # SELL
    # -----------------------------------------------------

    if trend == "SELL":

        (
            score,
            filters,
            reasons,
            sr,
            divergence
        ) = _analyze_sell(
            df15,
            df5
        )

        if score >= MIN_SCORE:
            return _build_signal(
                "SELL",
                score,
                trend,
                price,
                atr,
                rsi,
                adx,
                ema20,
                ema50,
                macd,
                macd_signal,
                sr,
                divergence,
                filters,
                reasons,
                candle_time
            )

        return _build_no_signal(
            trend,
            score,
            price,
            rsi,
            adx,
            atr,
            ema20,
            ema50,
            macd,
            macd_signal,
            sr,
            divergence,
            filters,
            reason