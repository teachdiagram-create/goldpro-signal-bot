# =========================================================
# GoldPro MTF Strategy V5 - CLEAN FINAL
#
# BUY:
#   1) 15M EMA20 > EMA50 = bullish trend
#   2) 5M RSI went below 30 and crossed back above 30
#   3) Last 5M candle bullish and closes above previous close
#   4) Price near 5M OR 15M support
#   5) Bullish RSI divergence = +10 bonus
#
# SELL:
#   1) 15M EMA20 < EMA50 = bearish trend
#   2) 5M RSI went above 70 and crossed back below 70
#   3) Last 5M candle bearish and closes below previous close
#   4) Price near 5M OR 15M resistance
#   5) Bearish RSI divergence = +10 bonus
#
# EMA20 / EMA50 ONLY define trend.
#
# MACD and ADX are NOT entry conditions.
#
# Minimum score = 70
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
    except (TypeError, ValueError):
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
    except Exception as exc:
        print("[MTF] Indicator error:", exc)
        return None


# =========================================================
# TREND
#
# EMA20 / EMA50 ONLY DEFINE TREND
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
# =========================================================

def _rsi_buy_trigger(df5):

    if df5 is None or len(df5) < 3:
        return False

    current = _safe_float(
        df5.iloc[-1].get("RSI")
    )

    previous = _safe_float(
        df5.iloc[-2].get("RSI")
    )

    before = _safe_float(
        df5.iloc[-3].get("RSI")
    )

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
# =========================================================

def _rsi_sell_trigger(df5):

    if df5 is None or len(df5) < 3:
        return False

    current = _safe_float(
        df5.iloc[-1].get("RSI")
    )

    previous = _safe_float(
        df5.iloc[-2].get("RSI")
    )

    before = _safe_float(
        df5.iloc[-3].get("RSI")
    )

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
# BULLISH CANDLE
# =========================================================

def _bullish_candle(df5):

    if df5 is None or len(df5) < 2:
        return False

    last = _latest(df5)
    prev = _previous(df5)

    close = _safe_float(last.get("close"))
    open_price = _safe_float(last.get("open"))
    prev_close = _safe_float(prev.get("close"))

    return (
        close > open_price
        and close > prev_close
    )


# =========================================================
# BEARISH CANDLE
# =========================================================

def _bearish_candle(df5):

    if df5 is None or len(df5) < 2:
        return False

    last = _latest(df5)
    prev = _previous(df5)

    close = _safe_float(last.get("close"))
    open_price = _safe_float(last.get("open"))
    prev_close = _safe_float(prev.get("close"))

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

    count = min(
        int(lookback),
        len(df)
    )

    if count <= 0:
        return None

    try:
        return float(
            df.iloc[-count:]["low"].min()
        )
    except Exception:
        return None


# =========================================================
# RESISTANCE
# =========================================================

def _find_resistance(df, lookback):

    if df is None or df.empty:
        return None

    count = min(
        int(lookback),
        len(df)
    )

    if count <= 0:
        return None

    try:
        return float(
            df.iloc[-count:]["high"].max()
        )
    except Exception:
        return None


# =========================================================
# SUPPORT CONTEXT
# =========================================================

def _support_context(df5, df15):

    price = _safe_float(
        _latest(df5).get("close")
    )

    atr = _safe_float(
        _latest(df5).get("ATR")
    )

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

    if support5 is not None:
        distance5 = abs(
            price - support5
        )
    else:
        distance5 = float("inf")

    if support15 is not None:
        distance15 = abs(
            price - support15
        )
    else:
        distance15 = float("inf")

    near5 = (
        distance5 <= max_distance
    )

    near15 = (
        distance15 <= max_distance
    )

    confirmed = (
        near5 or near15
    )

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

    price = _safe_float(
        _latest(df5).get("close")
    )

    atr = _safe_float(
        _latest(df5).get("ATR")
    )

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

    if resistance5 is not None:
        distance5 = abs(
            price - resistance5
        )
    else:
        distance5 = float("inf")

    if resistance15 is not None:
        distance15 = abs(
            price - resistance15
        )
    else:
        distance15 = float("inf")

    near5 = (
        distance5 <= max_distance
    )

    near15 = (
        distance15 <= max_distance
    )

    confirmed = (
        near5 or near15
    )

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

    try:
        idx1 = first["low"].idxmin()
        idx2 = second["low"].idxmin()

        price_low_1 = _safe_float(
            first.loc[idx1, "low"]
        )

        price_low_2 = _safe_float(
            second.loc[idx2, "low"]
        )

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

    except Exception:
        return False


# =========================================================
# BEARISH RSI DIVERGENCE
# =========================================================

def _bearish_divergence(df5):

    if df5 is None or len(df5) < 10:
        return False

    recent = df5.iloc[-10:]

    first = recent.iloc[:5]
    second = recent.iloc[5:]

    try:
        idx1 = first["high"].idxmax()
        idx2 = second["high"].idxmax()

        price_high_1 = _safe_float(
            first.loc[idx1, "high"]
        )

        price_high_2 = _safe_float(
            second.loc[idx2, "high"]
        )

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

    except Exception:
        return False


# =========================================================
# BUY ANALYSIS
# =========================================================

def _analyze_buy(df15, df5):

    trend_ok = (
        _get_trend_15m(df15)
        == "BUY"
    )

    rsi_ok = _rsi_buy_trigger(
        df5
    )

    candle_ok = _bullish_candle(
        df5
    )

    support_ok, sr = _support_context(
        df5,
        df15
    )

    divergence = _bullish_divergence(
        df5
    )

    score = 0
    reasons = []
    filters = {}

    # Trend = 20 points

    filters["Trend"] = trend_ok

    if trend_ok:
        score += 20
        reasons.append(
            "OK: EMA20 > EMA50 trend"
        )
    else:
        reasons.append(
            "WAIT: EMA trend"
        )

    # RSI reversal = 35 points

    filters["RSI Reversal"] = rsi_ok

    if rsi_ok:
        score += 35
        reasons.append(
            "OK: RSI below 30 -> back above 30"
        )
    else:
        reasons.append(
            "WAIT: RSI reversal"
        )

    # Candle = 20 points

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

    # Support = 15 points

    filters["Support"] = support_ok

    if support_ok:
        score += 15
        reasons.append(
            "OK: 5M/15M support"
        )
    else:
        reasons.append(
            "WAIT: 5M/15M support"
        )

    # Divergence = 10 bonus

    filters["RSI Divergence"] = divergence

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
# =========================================================

def _analyze_sell(df15, df5):

    trend_ok = (
        _get_trend_15m(df15)
        == "SELL"
    )

    rsi_ok = _rsi_sell_trigger(
        df5
    )

    candle_ok = _bearish_candle(
        df5
    )

    resistance_ok, sr = _resistance_context(
        df5,
        df15
    )

    divergence = _bearish_divergence(
        df5
    )

    score = 0
    reasons = []
    filters = {}

    # Trend = 20 points

    filters["Trend"] = trend_ok

    if trend_ok:
        score += 20
        reasons.append(
            "OK: EMA20 < EMA50 trend"
        )
    else:
        reasons.append(
            "WAIT: EMA trend"
        )

    # RSI reversal = 35 points

    filters["RSI Reversal"] = rsi_ok

    if rsi_ok:
        score += 35
        reasons.append(
            "OK: RSI above 70 -> back below 70"
        )
    else:
        reasons.append(
            "WAIT: RSI reversal"
        )

    # Candle = 20 points

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

    # Resistance = 15 points

    filters["Resistance"] = resistance_ok

    if resistance_ok:
        score += 15
        reasons.append(
            "OK: 5M/15M resistance"
        )
    else:
        reasons.append(
            "WAIT: 5M/15M resistance"
        )

    # Divergence = 10 bonus

    filters["RSI Divergence"] = divergence

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
# QUALITY
# =========================================================

def _quality(score):

    if score >= 85:
        return "STRONG"

    if score >= MIN_SCORE:
        return "NORMAL"

    return "WEAK"


# =========================================================
# COMMON DATA
# =========================================================

def _common_data(df5):

    last = _latest(df5)

    return {
        "price": _safe_float(
            last.get("close")
        ),

        "rsi": _safe_float(
            last.get("RSI")
        ),

        "adx": _safe_float(
            last.get("ADX")
        ),

        "atr": _safe_float(
            last.get("ATR")
        ),

        "ema20": _safe_float(
            last.get("EMA20")
        ),

        "ema50": _safe_float(
            last.get("EMA50")
        ),

        "macd": _safe_float(
            last.get("MACD")
        ),

        "macd_signal": _safe_float(
            last.get("MACD_SIGNAL")
        ),

        "time": str(
            last.get("time")
        )
    }


# =========================================================
# NO SIGNAL BUILDER
# =========================================================

def _build_no_signal(
    trend,
    score,
    reasons,
    filters,
    data,
    sr,
    divergence
):

    result = {
        "signal": "NO SIGNAL",
        "stage": "5M",
        "trend": trend,
        "score": score,
        "confidence": score,
        "quality": _quality(score),

        "reasons": [
            f"Score: {score}/100"
        ] + reasons,

        "filters": filters,
        "divergence": divergence
    }

    result.update(data)

    if trend == "BUY":

        result["support"] = sr.get(
            "support_5m"
        )

        result["support_15m"] = sr.get(
            "support_15m"
        )

    elif trend == "SELL":

        result["resistance"] = sr.get(
            "resistance_5m"
        )

        result["resistance_15m"] = sr.get(
            "resistance_15m"
        )

    return result


# =========================================================
# SIGNAL BUILDER
# =========================================================

def _build_signal(
    signal,
    trend,
    score,
    reasons,
    filters,
    data,
    sr,
    divergence
):

    price = data["price"]
    atr = data["atr"]

    if atr <= 0:

        return _build_no_signal(
            trend,
            score,
            reasons + [
                "WAIT: ATR unavailable"
            ],
            filters,
            data,
            sr,
            divergence
        )

    # BUY

    if signal == "BUY":

        sl = (
            price
            - atr * SL_ATR_MULTIPLIER
        )

        tp1 = (
            price
            + atr * TP1_ATR_MULTIPLIER
        )

        tp2 = (
            price
            + atr * TP2_ATR_MULTIPLIER
        )

    # SELL

    else:

        sl = (
            price
            + atr * SL_ATR_MULTIPLIER
        )

        tp1 = (
            price
            - atr * TP1_ATR_MULTIPLIER
        )

        tp2 = (
            price
            - atr * TP2_ATR_MULTIPLIER
        )

    result = {
        "signal": signal,
        "score": score,
        "confidence": score,
        "quality": _quality(score),
        "stage": "5M",
        "trend": trend,

        "price": price,
        "sl": sl,
        "tp1": tp1,
        "tp2": tp2,

        "rsi": data["rsi"],
        "adx": data["adx"],
        "atr": atr,

        "ema20": data["ema20"],
        "ema50": data["ema50"],

        "macd": data["macd"],
        "macd_signal": data["macd_signal"],

        "divergence": divergence,
        "filters": filters,
        "time": data["time"],

        "reasons": [
            f"Score: {score}/100"
        ] + reasons + [
            f"FINAL {signal} SIGNAL"
        ]
    }

    if signal == "BUY":

        result["support"] = sr.get(
            "support_5m"
        )

        result["support_15m"] = sr.get(
            "support_15m"
        )

    else:

        result["resistance"] = sr.get(
            "resistance_5m"
        )

        result["resistance_15m"] = sr.get(
            "resistance_15m"
        )

    return result


# =========================================================
# MAIN SIGNAL FUNCTION
# =========================================================

def generate_mtf_signal(
    df30,
    df15,
    df5
):

    # -----------------------------------------------------
    # DATA CHECK
    # -----------------------------------------------------

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
            "trend": "NONE",
            "score": 0,
            "confidence": 0,
            "quality": "WEAK",
            "reasons": [
                "Insufficient market data"
            ]
        }

    
    # -----------------------------------------------------
    # PREPARE INDICATORS
    # -----------------------------------------------------

    prepared30 = _prepare(
        df30
    )

    prepared15 = _prepare(
        df15
    )

    prepared5 = _prepare(
        df5
    )

    if (
        prepared30 is None
        or prepared15 is None
        or prepared5 is None
    ):

        return {
            "signal": "NO SIGNAL",
            "stage": "DATA",
            "trend": "NONE",
            "score": 0,
            "confidence": 0,
            "quality": "WEAK",
            "reasons": [
                "Indicator calculation failed"
            ]
        }

    # -----------------------------------------------------
    # USE PREPARED DATA
    # -----------------------------------------------------

    df30 = prepared30
    df15 = prepared15
    df5 = prepared5

    # -----------------------------------------------------
    # COMMON DATA
    # -----------------------------------------------------

    data = _common_data(
        df5
    )

    # -----------------------------------------------------
    # TREND
    #
    # EMA20 / EMA50 ONLY
    # -----------------------------------------------------

    trend = _get_trend_15m(
        df15
    )

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
                trend,
                score,
                reasons,
                filters,
                data,
                sr,
                divergence
            )

        return _build_no_signal(
            trend,
            score,
            reasons,
            filters,
            data,
            sr,
            divergence
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
                trend,
                score,
                reasons,
                filters,
                data,
                sr,
                divergence
            )

        return _build_no_signal(
            trend,
            score,
            reasons,
            filters,
            data,
            sr,
            divergence
        )

    # -----------------------------------------------------
    # NO CLEAR TREND
    # -----------------------------------------------------

    return {
        "signal": "NO SIGNAL",
        "stage": "15M",
        "trend": "NONE",
        "score": 0,
        "confidence": 0,
        "quality": "WEAK",

        "reasons": [
            "EMA20 and EMA50 have no clear trend"
        ],

        "filters": {},
        "divergence": False,

        "price": data["price"],
        "rsi": data["rsi"],
        "adx": data["adx"],
        "atr": data["atr"],
        "ema20": data["ema20"],
        "ema50": data["ema50"],
        "macd": data["macd"],
        "macd_signal": data["macd_signal"],
        "time": data["time"]
    }