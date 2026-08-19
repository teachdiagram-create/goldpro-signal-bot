from config import MIN_ADX

# =========================================================
# GoldPro MTF Strategy V4
#
# 30M Trend → 15M Confirmation → 5M Entry
#
# 8 Filters
# Minimum score: 70%
#
# 6/8 = 75%  -> SIGNAL
# 5/8 = 62.5% -> NO SIGNAL
# =========================================================


# ---------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------

MIN_SCORE_PERCENT = 70

RSI_BUY_MIN = 40
RSI_BUY_MAX = 75

RSI_SELL_MIN = 25
RSI_SELL_MAX = 60

ATR_SL = 1.5
ATR_TP1 = 2.0
ATR_TP2 = 3.0

RESISTANCE_BUFFER_ATR = 0.35
SUPPORT_BUFFER_ATR = 0.35


# =========================================================
# HELPERS
# =========================================================

def _latest(df):
    return df.iloc[-1]


def add_mtf_indicators(df):
    from indicators import add_indicators
    return add_indicators(df.copy())


# =========================================================
# BUILD 30M FROM 15M
# =========================================================

def build_30m_from_15m(df15):

    df = df15.copy()

    df["time"] = df["time"].astype(str)

    temp = df.copy()

    temp["time"] = __import__("pandas").to_datetime(
        temp["time"],
        errors="coerce",
        utc=True
    )

    temp = temp.set_index("time")

    df30 = temp.resample("30min").agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last"
    }).dropna().reset_index()

    print(
        "[30M] Built from 15M | Latest CLOSED candle:",
        df30.iloc[-1]["time"]
    )

    print(
        "[30M] Latest CLOSED close:",
        df30.iloc[-1]["close"]
    )

    return df30


# =========================================================
# 30M TREND
# =========================================================

def _trend_30m(df30):

    df30 = add_mtf_indicators(df30)

    last = _latest(df30)

    ema20 = float(last["EMA20"])
    ema50 = float(last["EMA50"])
    adx = float(last["ADX"])

    if ema20 > ema50 and adx >= MIN_ADX:
        return "BUY"

    if ema20 < ema50 and adx >= MIN_ADX:
        return "SELL"

    return "NONE"


# =========================================================
# 15M CONFIRMATION
# =========================================================

def _confirmation_15m(df15, direction):

    df15 = add_mtf_indicators(df15)

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
# SUPPORT / RESISTANCE
# =========================================================

def _support_resistance(df5):

    lookback = min(50, len(df5))

    recent = df5.iloc[-lookback:]

    support = float(recent["low"].min())
    resistance = float(recent["high"].max())

    return support, resistance


# =========================================================
# 5M FILTERS
# =========================================================

def _evaluate_5m(df5, direction):

    df5 = add_mtf_indicators(df5)

    last = _latest(df5)

    price = float(last["close"])
    open_ = float(last["open"])

    ema20 = float(last["EMA20"])
    ema50 = float(last["EMA50"])

    rsi = float(last["RSI"])
    adx = float(last["ADX"])
    atr = float(last["ATR"])

    macd = float(last["MACD"])
    macd_signal = float(last["MACD_SIGNAL"])

    support, resistance = _support_resistance(df5)

    # -----------------------------------------------------
    # FILTER 3
    # 5M EMA TREND
    # -----------------------------------------------------

    if direction == "BUY":
        ema_trend = ema20 > ema50
    else:
        ema_trend = ema20 < ema50

    # -----------------------------------------------------
    # FILTER 4
    # RSI
    # -----------------------------------------------------

    if direction == "BUY":

        rsi_ok = (
            RSI_BUY_MIN
            <= rsi
            <= RSI_BUY_MAX
        )

    else:

        rsi_ok = (
            RSI_SELL_MIN
            <= rsi
            <= RSI_SELL_MAX
        )

    # -----------------------------------------------------
    # FILTER 5
    # ADX
    # -----------------------------------------------------

    adx_ok = adx >= MIN_ADX

    # -----------------------------------------------------
    # FILTER 6
    # MACD
    # -----------------------------------------------------

    if direction == "BUY":

        macd_ok = (
            macd >= macd_signal
            or macd > 0
        )

    else:

        macd_ok = (
            macd <= macd_signal
            or macd < 0
        )

    # -----------------------------------------------------
    # FILTER 7
    # CANDLE
    # -----------------------------------------------------

    if direction == "BUY":

        candle_ok = (
            close_is_bullish(open_, price)
        )

    else:

        candle_ok = (
            close_is_bearish(open_, price)
        )

    # -----------------------------------------------------
    # SUPPORT / RESISTANCE
    # -----------------------------------------------------

    distance_to_support = abs(
        price - support
    )

    distance_to_resistance = abs(
        resistance - price
    )

    near_support = (
        distance_to_support
        <= atr * SUPPORT_BUFFER_ATR
    )

    near_resistance = (
        distance_to_resistance
        <= atr * RESISTANCE_BUFFER_ATR
    )

    # -----------------------------------------------------
    # BREAKOUT DETECTION
    # -----------------------------------------------------

    breakout_resistance = (
        price > resistance
    )

    breakout_support = (
        price < support
    )

    # -----------------------------------------------------
    # FILTER 8
    # ENTRY CONTEXT
    #
    # Important:
    # Strong trend should NOT be blocked simply because
    # price is close to resistance/support.
    # A breakout is considered valid.
    # -----------------------------------------------------

    if direction == "BUY":

        if breakout_resistance:
            entry_context = True

        elif near_resistance:
            entry_context = False

        else:
            entry_context = True

    else:

        if breakout_support:
            entry_context = True

        elif near_support:
            entry_context = False

        else:
            entry_context = True

    # -----------------------------------------------------
    # EXTENSION
    # -----------------------------------------------------

    distance_from_ema = abs(
        price - ema20
    )

    entry_not_extended = (
        distance_from_ema <= atr * 2.0
    )

    # -----------------------------------------------------
    # FILTER LIST
    # -----------------------------------------------------

    filters = {
        "5M EMA Trend": ema_trend,
        "RSI": rsi_ok,
        "ADX": adx_ok,
        "MACD": macd_ok,
        "5M Candle": candle_ok,
        "Entry Context": entry_context
    }

    return {
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

        "distance_to_support":
            distance_to_support,

        "distance_to_resistance":
            distance_to_resistance,

        "near_support":
            near_support,

        "near_resistance":
            near_resistance,

        "breakout_resistance":
            breakout_resistance,

        "breakout_support":
            breakout_support,

        "distance_from_ema":
            distance_from_ema,

        "entry_not_extended":
            entry_not_extended,

        "filters":
            filters,

        "time":
            str(last["time"])
    }


# =========================================================
# CANDLE HELPERS
# =========================================================

def close_is_bullish(open_, close):
    return close > open_


def close_is_bearish(open_, close):
    return close < open_


# =========================================================
# MAIN SIGNAL
# =========================================================

def generate_mtf_signal(df30, df15, df5):

    # =====================================================
    # BUILD / PREPARE 30M
    # =====================================================

    df30 = add_mtf_indicators(df30)

    # =====================================================
    # 30M TREND
    # =====================================================

    last30 = _latest(df30)

    ema20_30 = float(last30["EMA20"])
    ema50_30 = float(last30["EMA50"])
    adx30 = float(last30["ADX"])

    if (
        ema20_30 > ema50_30
        and adx30 >= MIN_ADX
    ):

        direction = "BUY"

    elif (
        ema20_30 < ema50_30
        and adx30 >= MIN_ADX
    ):

        direction = "SELL"

    else:

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

    confirmation, c15 = _confirmation_15m(
        df15,
        direction
    )

    if not confirmation:

        return {
            "signal": "NO SIGNAL",
            "stage": "15M",
            "trend": direction,
            "reasons": [
                "30M trend confirmed",
                "15M confirmation not ready"
            ],
            **c15
        }

    # =====================================================
    # 5M
    # =====================================================

    s = _evaluate_5m(
        df5,
        direction
    )

    filters = s["filters"]

    # =====================================================
    # 8 FILTER SCORE
    # =====================================================

    filter_results = {

        "30M Trend":
            True,

        "15M Confirmation":
            confirmation,

        "5M EMA Trend":
            filters["5M EMA Trend"],

        "RSI":
            filters["RSI"],

        "ADX":
            filters["ADX"],

        "MACD":
            filters["MACD"],

        "5M Candle":
            filters["5M Candle"],

        "Entry Context":
            filters["Entry Context"]
    }

    passed = sum(
        1
        for value in filter_results.values()
        if value
    )

    total = len(filter_results)

    confidence = (
        passed / total
    ) * 100

    # =====================================================
    # QUALITY
    # =====================================================

    if passed >= 7:

        quality = "STRONG"

    elif passed == 6:

        quality = "NORMAL"

    else:

        quality = "WEAK"

    # =====================================================
    # REASONS
    # =====================================================

    reasons = [
        f"Filters: {passed}/{total} ({confidence:.0f}%)"
    ]

    for name, value in filter_results.items():

        if value:

            reasons.append(
                f"OK: {name}"
            )

        else:

            reasons.append(
                f"WAIT: {name}"
            )

    # =====================================================
    # SIGNAL THRESHOLD
    #
    # 70% of 8 = 5.6
    # Therefore minimum integer = 6
    # =====================================================

    minimum_filters = 6

    if passed < minimum_filters:

        return {
            "signal": "NO SIGNAL",
            "stage": "5M",
            "trend": direction,

            "reasons": reasons,

            **c15,
            **s,

            "filter_count":
                passed,

            "total_filters":
                total,

            "confidence":
                confidence,

            "quality":
                quality,

            "filters":
                filter_results
        }

    # =====================================================
    # FINAL SIGNAL
    # =====================================================

    signal = direction

    price = s["price"]
    atr = s["atr"]

    # -----------------------------------------------------
    # BUY
    # -----------------------------------------------------

    if signal == "BUY":

        sl = (
            price
            - atr * ATR_SL
        )

        tp1 = (
            price
            + atr * ATR_TP1
        )

        tp2 = (
            price
            + atr * ATR_TP2
        )

    # -----------------------------------------------------
    # SELL
    # -----------------------------------------------------

    else:

        sl = (
            price
            + atr * ATR_SL
        )

        tp1 = (
            price
            - atr * ATR_TP1
        )

        tp2 = (
            price
            - atr * ATR_TP2
        )

    # =====================================================
    # FINAL REASONS
    # =====================================================

    reasons.append(
        f"FINAL {signal} SIGNAL"
    )

    # =====================================================
    # RESULT
    # =====================================================

    return {

        "signal":
            signal,

        "score":
            passed,

        "confidence":
            confidence,

        "quality":
            quality,

        "reasons":
            reasons,

        "price":
            price,

        "sl":
            sl,

        "tp1":
            tp1,

        "tp2":
            tp2,

        "rsi":
            s["rsi"],

        "adx":
            s["adx"],

        "atr":
            s["atr"],

        "support":
            s["support"],

        "resistance":
            s["resistance"],

        "filter_count":
            passed,

        "total_filters":
            total,

        "filters":
            filter_results,

        "stage":
            "5M",

        "trend":
            direction,

        "time":
            s["time"]
    }