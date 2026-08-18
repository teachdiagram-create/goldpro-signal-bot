from config import MIN_ADX

# =========================================================
# GoldPro MTF Strategy
# 15M Trend → 5M Pullback → 1M Trigger
# =========================================================

RSI_BUY_MIN = 40
RSI_BUY_MAX = 65

RSI_SELL_MIN = 35
RSI_SELL_MAX = 60

PULLBACK_ATR = 0.75


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

    if ema20 > ema50 and adx >= MIN_ADX:
        return "BUY"

    if ema20 < ema50 and adx >= MIN_ADX:
        return "SELL"

    return "NONE"


# =========================================================
# 5M PULLBACK SETUP
# =========================================================

def _setup_5m(df5, direction):

    last = _latest(df5)

    price = float(last["close"])
    ema20 = float(last["EMA20"])
    ema50 = float(last["EMA50"])
    rsi = float(last["RSI"])
    adx = float(last["ADX"])
    atr = float(last["ATR"])

    # -----------------------------------------------------
    # 5M trend
    # -----------------------------------------------------

    if direction == "BUY":

        trend_ok = ema20 > ema50

        rsi_ok = (
            RSI_BUY_MIN <= rsi <= RSI_BUY_MAX
        )

        # Price must be reasonably close to EMA20.
        pullback = (
            ema20 - atr * PULLBACK_ATR
            <= price
            <= ema20 + atr * PULLBACK_ATR
        )

    else:

        trend_ok = ema20 < ema50

        rsi_ok = (
            RSI_SELL_MIN <= rsi <= RSI_SELL_MAX
        )

        # Price must be reasonably close to EMA20.
        pullback = (
            ema20 - atr * PULLBACK_ATR
            <= price
            <= ema20 + atr * PULLBACK_ATR
        )

    adx_ok = adx >= MIN_ADX

    setup = (
        trend_ok
        and rsi_ok
        and adx_ok
        and pullback
    )

    return setup, {
        "price": price,
        "rsi": rsi,
        "adx": adx,
        "atr": atr,
        "ema20": ema20,
        "ema50": ema50,
        "macd": float(last["MACD"]),
        "macd_signal": float(last["MACD_SIGNAL"]),
        "time": str(last["time"])
    }


# =========================================================
# 1M ENTRY TRIGGER
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

        trigger = (
            close > open_
            and close > prev_close
            and close >= ema
            and rsi >= 45
            and macd >= macd_sig
        )

        if trigger:
            return True, "1M bullish trigger"

        return False, "Waiting for 1M bullish trigger"

    # =====================================================
    # SELL
    # =====================================================

    trigger = (
        close < open_
        and close < prev_close
        and close <= ema
        and rsi <= 55
        and macd <= macd_sig
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
    # 15M
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
    # 5M
    # =====================================================

    setup, s = _setup_5m(
        df5,
        direction
    )

    if not setup:

        return {
            "signal": "NO SIGNAL",
            "stage": "5M",
            "trend": direction,
            "reasons": [
                "15M trend confirmed",
                "5M pullback not ready"
            ],
            **s
        }

    # =====================================================
    # 5M READY → WAIT FOR 1M
    # =====================================================

    if df1 is None:

        return {
            "signal": "NO SIGNAL",
            "stage": "1M",
            "trend": direction,
            "reasons": [
                "15M trend confirmed",
                "5M pullback ready",
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
                "5M pullback ready",
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
            "5M pullback setup",
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
        "trend": direction
    }