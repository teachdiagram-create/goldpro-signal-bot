from config import MIN_ADX

# =========================================================
# GoldPro MTF Strategy
# 15M Trend → Historical 5M Pullback → 1M Trigger
# =========================================================

RSI_BUY_MIN = 40
RSI_BUY_MAX = 68

RSI_SELL_MIN = 32
RSI_SELL_MAX = 60

# چند کندل 5M اخیر برای پیدا کردن Pullback
PULLBACK_LOOKBACK = 8

# فاصله قابل قبول Pullback از EMA20 بر اساس ATR
PULLBACK_ATR = 0.90

# حداکثر فاصله برای جلوگیری از ورود دیرهنگام
MAX_ENTRY_ATR = 1.50


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
# HISTORICAL 5M PULLBACK
# =========================================================

def _find_recent_pullback(df5, direction):

    if len(df5) < 3:
        return False, None

    start = max(0, len(df5) - PULLBACK_LOOKBACK)

    recent = df5.iloc[start:]

    for i in range(len(recent) - 1, -1, -1):

        row = recent.iloc[i]

        price = float(row["close"])
        ema20 = float(row["EMA20"])
        atr = float(row["ATR"])

        if atr <= 0:
            continue

        distance = abs(price - ema20)

        # -------------------------
        # BUY pullback
        # -------------------------

        if direction == "BUY":

            ema20_ok = (
                abs(price - ema20)
                <= atr * PULLBACK_ATR
            )

            if ema20_ok:
                return True, row

        # -------------------------
        # SELL pullback
        # -------------------------

        else:

            ema20_ok = (
                abs(price - ema20)
                <= atr * PULLBACK_ATR
            )

            if ema20_ok:
                return True, row

    return False, None


# =========================================================
# 5M SETUP
# =========================================================

def _setup_5m(df5, direction):

    last = _latest(df5)

    price = float(last["close"])
    ema20 = float(last["EMA20"])
    ema50 = float(last["EMA50"])
    rsi = float(last["RSI"])
    adx = float(last["ADX"])
    atr = float(last["ATR"])

    macd = float(last["MACD"])
    macd_signal = float(last["MACD_SIGNAL"])

    # -----------------------------------------------------
    # Current 5M trend
    # -----------------------------------------------------

    if direction == "BUY":

        trend_ok = ema20 > ema50

        rsi_ok = (
            RSI_BUY_MIN <= rsi <= RSI_BUY_MAX
        )

    else:

        trend_ok = ema20 < ema50

        rsi_ok = (
            RSI_SELL_MIN <= rsi <= RSI_SELL_MAX
        )

    adx_ok = adx >= MIN_ADX

    # -----------------------------------------------------
    # Historical pullback
    # -----------------------------------------------------

    pullback_found, pullback_row = _find_recent_pullback(
        df5,
        direction
    )

    # -----------------------------------------------------
    # Current distance from EMA20
    # -----------------------------------------------------

    distance_from_ema = abs(price - ema20)

    entry_not_extended = (
        distance_from_ema <= atr * MAX_ENTRY_ATR
    )

    # -----------------------------------------------------
    # Momentum
    # -----------------------------------------------------

    if direction == "BUY":

        momentum_ok = (
            macd >= macd_signal
            or macd > 0
        )

    else:

        momentum_ok = (
            macd <= macd_signal
            or macd < 0
        )

    # -----------------------------------------------------
    # Final setup
    # -----------------------------------------------------

    setup = (
        trend_ok
        and adx_ok
        and pullback_found
        and entry_not_extended
        and momentum_ok
    )

    reasons = [
        "15M trend confirmed"
    ]

    if pullback_found:
        reasons.append("Recent 5M pullback found")
    else:
        reasons.append("No recent 5M pullback")

    if entry_not_extended:
        reasons.append("Entry distance acceptable")
    else:
        reasons.append("Entry too late after pullback")

    if momentum_ok:
        reasons.append("5M momentum confirmed")

    if not rsi_ok:
        reasons.append("RSI outside ideal zone")

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
        "entry_not_extended": entry_not_extended,
        "pullback_found": pullback_found,
        "pullback_time": (
            str(pullback_row["time"])
            if pullback_row is not None
            else None
        ),
        "reasons": reasons
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

        return {
            "signal": "NO SIGNAL",
            "stage": "5M",
            "trend": direction,
            "reasons": s["reasons"],
            **s
        }

    # =====================================================
    # WAIT FOR 1M
    # =====================================================

    if df1 is None:

        return {
            "signal": "NO SIGNAL",
            "stage": "1M",
            "trend": direction,
            "reasons": [
                *s["reasons"],
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
                *s["reasons"],
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
            *s["reasons"],
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

        "pullback_time": s["pullback_time"]
    }