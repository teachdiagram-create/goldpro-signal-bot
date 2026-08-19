from config import MIN_ADX

# =========================================================
# GoldPro MTF Strategy
# 30M Trend → 15M Confirmation → 5M Entry
# =========================================================

RSI_BUY_MIN = 35
RSI_BUY_MAX = 68

RSI_SELL_MIN = 32
RSI_SELL_MAX = 65

# حداکثر فاصله قیمت از EMA20 بر اساس ATR
MAX_ENTRY_DISTANCE_ATR = 1.20


def _latest(df):
    return df.iloc[-1]


def add_mtf_indicators(df):
    from indicators import add_indicators
    return add_indicators(df.copy())


# =========================================================
# 30M MAIN TREND
# =========================================================

def _trend_30m(df30):

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
# 5M ENTRY
# =========================================================

def _entry_5m(df5, direction):

    last = _latest(df5)

    prev = (
        df5.iloc[-2]
        if len(df5) >= 2
        else None
    )

    price = float(last["close"])
    open_price = float(last["open"])

    ema20 = float(last["EMA20"])
    ema50 = float(last["EMA50"])

    rsi = float(last["RSI"])
    adx = float(last["ADX"])
    atr = float(last["ATR"])

    macd = float(last["MACD"])
    macd_signal = float(last["MACD_SIGNAL"])

    distance_from_ema = abs(
        price - ema20
    )

    entry_not_extended = (
        distance_from_ema
        <= atr * MAX_ENTRY_DISTANCE_ATR
    )

    # -----------------------------------------------------
    # BUY
    # -----------------------------------------------------

    if direction == "BUY":

        trend_ok = ema20 > ema50

        rsi_ok = (
            RSI_BUY_MIN
            <= rsi
            <= RSI_BUY_MAX
        )

        momentum_ok = (
            macd >= macd_signal
            or (
                prev is not None
                and macd > float(prev["MACD"])
            )
        )

        candle_ok = (
            price >= open_price
        )

    # -----------------------------------------------------
    # SELL
    # -----------------------------------------------------

    else:

        trend_ok = ema20 < ema50

        rsi_ok = (
            RSI_SELL_MIN
            <= rsi
            <= RSI_SELL_MAX
        )

        momentum_ok = (
            macd <= macd_signal
            or (
                prev is not None
                and macd < float(prev["MACD"])
            )
        )

        candle_ok = (
            price <= open_price
        )

    setup = (
        trend_ok
        and rsi_ok
        and adx >= MIN_ADX
        and momentum_ok
        and candle_ok
        and entry_not_extended
    )

    return setup, {
        "price": price,
        "rsi": rsi,
        "adx": adx,
        "atr": atr,
        "ema20": ema20,
        "ema50": ema50,
        "macd": macd,
        "macd_signal": macd_signal,
        "distance_from_ema": distance_from_ema,
        "entry_not_extended": entry_not_extended,
        "time": str(last["time"])
    }


# =========================================================
# MAIN SIGNAL
# =========================================================

def generate_mtf_signal(
    df30,
    df15,
    df5
):

    df30 = add_mtf_indicators(df30)
    df15 = add_mtf_indicators(df15)
    df5 = add_mtf_indicators(df5)

    # =====================================================
    # 30M TREND
    # =====================================================

    direction = _trend_30m(df30)

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

    confirmed, confirmation = _confirm_15m(
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
                "15M confirmation not ready"
            ],
            **confirmation
        }

    # =====================================================
    # 5M ENTRY
    # =====================================================

    setup, entry = _entry_5m(
        df5,
        direction
    )

    if not setup:

        return {
            "signal": "NO SIGNAL",
            "stage": "5M",
            "trend": direction,
            "reasons": [
                "30M trend confirmed",
                "15M confirmation confirmed",
                "5M entry not ready"
            ],
            **confirmation,
            **entry
        }

    # =====================================================
    # FINAL SIGNAL
    # =====================================================

    signal = direction

    score = 80
    confidence = 80
    quality = "STRONG"

    price = entry["price"]
    atr = entry["atr"]

    if signal == "BUY":

        sl = price - (
            atr * 1.5
        )

        tp1 = price + (
            atr * 2
        )

        tp2 = price + (
            atr * 3
        )

    else:

        sl = price + (
            atr * 1.5
        )

        tp1 = price - (
            atr * 2
        )

        tp2 = price - (
            atr * 3
        )

    return {

        "signal": signal,

        "score": score,

        "confidence": confidence,

        "quality": quality,

        "reasons": [
            "30M trend confirmed",
            "15M confirmation confirmed",
            "5M entry setup"
        ],

        "price": price,

        "sl": sl,

        "tp1": tp1,

        "tp2": tp2,

        "rsi": entry["rsi"],

        "adx": entry["adx"],

        "atr": entry["atr"],

        "stage": "5M",

        "trend": direction
    }