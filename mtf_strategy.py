# =========================================================
# GoldPro MTF Strategy V5
#
# Strategy:
# BUY:
#   1) 15M EMA20 > EMA50  -> bullish trend only
#   2) 5M RSI went below 30 and crossed back above 30
#   3) Last 5M candle bullish and closes above previous close
#   4) Price near 5M + 15M support
#   5) Bullish RSI divergence = bonus
#
# SELL:
#   1) 15M EMA20 < EMA50  -> bearish trend only
#   2) 5M RSI went above 70 and crossed back below 70
#   3) Last 5M candle bearish and closes below previous close
#   4) Price near 5M + 15M resistance
#   5) Bearish RSI divergence = bonus
#
# EMA20 / EMA50:
# ONLY trend direction.
#
# Minimum score:
# 70 / 100
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
# HELPERS
# =========================================================

def _latest(df):
    return df.iloc[-1]


def _previous(df):
    return df.iloc[-2]


def _prepare(df):
    if df is None or df.empty:
        return None

    return add_indicators(df.copy())


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


# =========================================================
# TREND
#
# EMA ONLY DEFINES TREND
# =========================================================

def _get_trend_15m(df15):

    last = _latest(df15)

    ema20 = _safe_float(last["EMA20"])
    ema50 = _safe_float(last["EMA50"])

    if ema20 > ema50:
        return "BUY"

    if ema20 < ema50:
        return "SELL"

    return "NONE"


# =========================================================
# RSI REVERSAL
# =========================================================

def _rsi_buy_trigger(df5):

    if len(df5) < 3:
        return False

    current = _safe_float(df5.iloc[-1]["RSI"])
    previous = _safe_float(df5.iloc[-2]["RSI"])
    before = _safe_float(df5.iloc[-3]["RSI"])

    # RSI must have been below 30
    # and then cross back above 30.

    went_oversold = (
        before < RSI_OVERSOLD
        or previous < RSI_OVERSOLD
    )

    crossed_back = (
        previous <= RSI_OVERSOLD
        and current > RSI_OVERSOLD
    )

    return went_oversold and crossed_back


def _rsi_sell_trigger(df5):

    if len(df5) < 3:
        return False

    current = _safe_float(df5.iloc[-1]["RSI"])
    previous = _safe_float(df5.iloc[-2]["RSI"])
    before = _safe_float(df5.iloc[-3]["RSI"])

    # RSI must have been above 70
    # and then cross back below 70.

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

    if len(df5) < 2:
        return False

    last = _latest(df5)
    prev = _previous(df5)

    close = _safe_float(last["close"])
    open_price = _safe_float(last["open"])
    prev_close = _safe_float(prev["close"])

    return (
        close > open_price
        and close > prev_close
    )


def _bearish_candle(df5):

    if len(df5) < 2:
        return False

    last = _latest(df5)
    prev = _previous(df5)

    close = _safe_float(last["close"])
    open_price = _safe_float(last["open"])
    prev_close = _safe_float(prev["close"])

    return (
        close < open_price
        and close < prev_close
    )


# =========================================================
# SUPPORT / RESISTANCE
# =========================================================

def _find_support(df, lookback):

    if df is None or len(df) < lookback:
        lookback = len(df)

    if lookback <= 0:
        return None

    recent = df.iloc[-lookback:]

    return _safe_float(
        recent["low"].min()
    )


def _find_resistance(df, lookback):

    if df is None or len(df) < lookback:
        lookback = len(df)

    if lookback <= 0:
        return None

    recent = df.iloc[-lookback:]

    return _safe_float(
        recent["high"].max()
    )


# =========================================================
# SUPPORT / RESISTANCE CONFIRMATION
# =========================================================

def _support_context(df5, df15):

    price = _safe_float(
        _latest(df5)["close"]
    )

    atr = _safe_float(
        _latest(df5)["ATR"]
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

    distance5 = abs(price - support5)
    distance15 = abs(price - support15)

    near5 = distance5 <= max_distance
    near15 = distance15 <= max_distance

    # Accept when support from either timeframe
    # is close enough. This prevents the strategy
    # from becoming too restrictive.

    confirmed = near5 or near15

    return confirmed, {
        "support_5m": support5,
        "support_15m": support15,
        "distance_to_support_5m": distance5,
        "distance_to_support_15m": distance15,
        "near_support_5m": near5,
        "near_support_15m": near15
    }


def _resistance_context(df5, df15):

    price = _safe_float(
        _latest(df5)["close"]
    )

    atr = _safe_float(
        _latest(df5)["ATR"]
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

    distance5 = abs(price - resistance5)
    distance15 = abs(price - resistance15)

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
# RSI DIVERGENCE
# =========================================================

def _bullish_divergence(df5):

    if len(df5) < 10:
        return False

    recent = df5.iloc[-10:]

    # First half
    first = recent.iloc[:5]

    # Second half
    second = recent.iloc[5:]

    price_low_1 = _safe_float(
        first["low"].min()
    )

    price_low_2 = _safe_float(
        second["low"].min()
    )

    rsi_at_low_1 = _safe_float(
        first.loc[
            first["low"].idxmin(),
            "RSI"
        ]
    )

    rsi_at_low_2 = _safe_float(
        second.loc[
            second["low"].idxmin(),
            "RSI"
        ]
    )

    # Price lower low + RSI higher low
    return (
        price_low_2 < price_low_1
        and rsi_at_low_2 > rsi_at_low_1
    )


def _bearish_divergence(df5):

    if len(df5) < 10:
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

    rsi_at_high_1 = _safe_float(
        first.loc[
            first["high"].idxmax(),
            "RSI"
        ]
    )

    rsi_at_high_2 = _safe_float(
        second.loc[
            second["high"].idxmax(),
            "RSI"
        ]
    )

    # Price higher high + RSI lower high
    return (
        price_high_2 > price_high_1
        and rsi_at_high_2 < rsi_at_high_1
    )


# =========================================================
# BUY ANALYSIS
# =========================================================

def _analyze_buy(df15, df5):

    last = _latest(df5)

    trend = _get_trend_15m(df15)

    rsi_trigger = _rsi_buy_trigger(df5)

    candle_ok = _bullish_candle(df5)

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

    # -----------------------------------------------------
    # TREND
    # -----------------------------------------------------

    filters["Trend"] = trend == "BUY"

    if filters["Trend"]:
        score += 20
        reasons.append("OK: EMA20 > EMA50 trend")

    else:
        reasons.append("WAIT: EMA trend")

    # -----------------------------------------------------
    # RSI
    # -----------------------------------------------------

    filters["RSI Reversal"] = rsi_trigger

    if rsi_trigger:
        score += 35
        reasons.append(
            "OK: RSI below 30 → back above 30"
        )

    else:
        reasons.append(
            "WAIT: RSI reversal"
        )

    # -----------------------------------------------------
    # CANDLE
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # SUPPORT
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # DIVERGENCE BONUS
    # -----------------------------------------------------

    if divergence:
        score += 10
        reasons.append(
            "BONUS: bullish RSI divergence"
        )

    else:
        reasons.append(
            "No bullish divergence"
        )

    return score, filters, reasons, sr, divergence


# =========================================================
# SELL ANALYSIS
# =========================================================

def _analyze_sell(df15, df5):

    trend = _get_trend_15m(df15)

    rsi_trigger = _rsi_sell_trigger(df5)

    candle_ok = _bearish_candle(df5)

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

    # -----------------------------------------------------
    # TREND
    # -----------------------------------------------------

    filters["Trend"] = trend == "SELL"

    if filters["Trend"]:
        score += 20
        reasons.append(
            "OK: EMA20 < EMA50 trend"
        )

    else:
        reasons.append(
            "WAIT: EMA trend"
        )

    # -----------------------------------------------------
    # RSI
    # -----------------------------------------------------

    filters["RSI Reversal"] = rsi_trigger

    if rsi_trigger:
        score += 35
        reasons.append(
            "OK: RSI above 70 → back below 70"
        )

    else:
        reasons.append(
            "WAIT: RSI reversal"
        )

    # -----------------------------------------------------
    # CANDLE
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # RESISTANCE
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # DIVERGENCE BONUS
    # -----------------------------------------------------

    if divergence:
        score += 10
        reasons.append(
            "BONUS: bearish RSI divergence"
        )

    else:
        reasons.append(
            "No bearish divergence"
        )

    return score, filters, reasons, sr, divergence


# =========================================================
# MAIN SIGNAL
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
            "reasons": [
                "Insufficient market data"
            ]
        }

    # Add indicators
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
            "reasons": [
                "Indicator calculation failed"
            ]
        }

    # -----------------------------------------------------
    # TREND
    # -----------------------------------------------------

    trend = _get_trend_15m(df15)

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

        signal = "BUY"

        if score >= MIN_SCORE:

            sl = price - (
                atr * SL_ATR_MULTIPLIER
            )

            tp1 = price + (
                atr * TP1_ATR_MULTIPLIER
            )

            tp2 = price + (
                atr * TP2_ATR_MULTIPLIER
            )

            quality = (
                "STRONG"
                if score >= 85
                else "NORMAL"
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

                "support": sr.get(
                    "support_5m"
                ),

                "support_15m": sr.get(
                    "support_15m"
                ),

                "divergence": divergence,

                "reasons": [
                    f"Score: {score}/100"
                ] + reasons + [
                    "FINAL BUY SIGNAL"
                ],

                "filters": filters,
                "time": str(last["time"])
            }

        return {
            "signal": "NO SIGNAL",
            "stage": "5M",
            "trend": trend,
            "score": score,
            "confidence": score,
            "quality": (
                "STRONG"
                if score >= 85
                else "NORMAL"
                if score >= 70
                else "WEAK"
            ),
            "reasons": [
                f"Score: {score}/100"
            ] + reasons,
            "price": price,
            "rsi": rsi,
            "adx": adx,
            "atr": atr,
            "ema20": ema20,
            "ema50": ema50,
            "support": sr.get(
                "support_5m"
            ),
            "support_15m": sr.get(
                "support_15m"
            ),
            "divergence": divergence,
            "filters": filters,
            "time": str(last["time"])
        }

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

        signal = "SELL"

        if score >= MIN_SCORE:

            sl = price + (
                atr * SL_ATR_MULTIPLIER
            )

            tp1 = price - (
                atr * TP1_ATR_MULTIPLIER
            )

            tp2 = price - (
                atr * TP2_ATR_MULTIPLIER
            )

            quality = (
                "STRONG"
                if score >= 85
                else "NORMAL"
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

                "resistance": sr.get(
                    "resistance_5m"
                ),

                "resistance_15m": sr.get(
                    "resistance_15m"
                ),

                "divergence": divergence,

                "reasons": [
                    f"Score: {score}/100"
                ] + reasons + [
                    "FINAL SELL SIGNAL"
                ],

                "filters": filters,
                "time": str(last["time"])
            }

        return {
            "signal": "NO SIGNAL",
            "stage": "5M",
            "trend": trend,
            "score": score,
            "confidence": score,
            "quality": (
                "STRONG"
                if score >= 85
                else "NORMAL"
                if score >= 70
                else "WEAK"
            ),
            "reasons": [
                f"Score: {score}/100"
            ] + reasons,
            "price": price,
            "rsi": rsi,
            "adx": adx,
            "atr": atr,
            "ema20": ema20,
            "ema50": ema50,
            "resistance": sr.get(
                "resistance_5m"
            ),
            "resistance_15m": sr.get(
                "resistance_15m"
            ),
            "divergence": divergence,
            "filters": filters,
            "time": str(last["time"])
        }

    # -----------------------------------------------------
    # NO TREND
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
        "price": price,
        "rsi": rsi,
        "adx": adx,
        "atr": atr,
        "ema20": ema20,
        "ema50": ema50,
        "macd": macd,
        "macd_signal": macd_signal,
        "time": str(last["time"])
    }
        