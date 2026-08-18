from config import MIN_ADX

# =========================================================
# GoldPro MTF Strategy
# 15M Trend → 5M Pullback History → Entry Window → 1M Trigger
# =========================================================

RSI_BUY_MIN = 40
RSI_BUY_MAX = 65

RSI_SELL_MIN = 35
RSI_SELL_MAX = 60

# فاصله مجاز Pullback از EMA20 بر اساس ATR
PULLBACK_ATR = 0.75

# حداکثر تعداد کندل‌هایی که Pullback قبلی معتبر می‌ماند
MAX_PULLBACK_CANDLES = 4

# اگر قیمت بیشتر از این مقدار ATR از EMA20 دور شده باشد،
# ورود جدید ممنوع می‌شود
MAX_ENTRY_DISTANCE_ATR = 1.25


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
# 5M PULLBACK HISTORY
# =========================================================

def _find_recent_pullback(df5, direction):

    if df5 is None or len(df5) < 3:
        return False, None

    start = max(0, len(df5) - MAX_PULLBACK_CANDLES - 1)

    # فقط کندل‌های بسته‌شده اخیر
    recent = df5.iloc[start:-1]

    for i in range(len(recent) - 1, -1, -1):

        candle = recent.iloc[i]

        price = float(candle["close"])
        ema20 = float(candle["EMA20"])
        atr = float(candle["ATR"])

        if atr <= 0:
            continue

        distance = abs(price - ema20)

        # Pullback باید نزدیک EMA20 اتفاق افتاده باشد
        if distance <= atr * PULLBACK_ATR:

            candle_index = recent.index[i]
            current_index = df5.index[-1]

            try:
                candles_ago = list(df5.index).index(
                    current_index
                ) - list(df5.index).index(
                    candle_index
                )
            except Exception:
                candles_ago = 1

            return True, {
                "pullback_price": price,
                "pullback_ema20": ema20,
                "pullback_atr": atr,
                "pullback_time": str(candle["time"]),
                "candles_ago": candles_ago
            }

    return False, None


# =========================================================
# 5M CURRENT SETUP
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
    # Trend
    # -----------------------------------------------------

    if direction == "BUY":

        trend_ok = ema20 > ema50

    else:

        trend_ok = ema20 < ema50

    # -----------------------------------------------------
    # ADX
    # -----------------------------------------------------

    adx_ok = adx >= MIN_ADX

    # -----------------------------------------------------
    # Pullback history
    # -----------------------------------------------------

    pullback_found, pullback_info = _find_recent_pullback(
        df5,
        direction
    )

    # -----------------------------------------------------
    # Current distance from EMA20
    # -----------------------------------------------------

    distance_from_ema = abs(
        price - ema20
    )

    entry_not_extended = (
        distance_from_ema
        <= atr * MAX_ENTRY_DISTANCE_ATR
    )

    # -----------------------------------------------------
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
    # Momentum
    # -----------------------------------------------------

    if len(df5) >= 2:

        previous = df5.iloc[-2]

        previous_macd = float(
            previous["MACD"]
        )

        previous_signal = float(
            previous["MACD_SIGNAL"]
        )

    else:

        previous_macd = macd
        previous_signal = macd_signal

    current_diff = (
        macd - macd_signal
    )

    previous_diff = (
        previous_macd
        - previous_signal
    )

    if direction == "BUY":

        momentum_ok = (
            macd >= macd_signal
            or current_diff > previous_diff
        )

    else:

        momentum_ok = (
            macd <= macd_signal
            or current_diff < previous_diff
        )

    # -----------------------------------------------------
    # Final setup
    # -----------------------------------------------------

    setup = (
        trend_ok
        and adx_ok
        and pullback_found
        and entry_not_extended
        and rsi_ok
        and momentum_ok
    )

    info = {
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
    }

    if pullback_info:
        info.update(pullback_info)

    return setup, info


# =========================================================
# 1M ENTRY TRIGGER
# =========================================================

def _trigger_1m(df1, direction):

    if df1 is None or len(df1) < 3:
        return False, "Not enough 1M candles"

    last = df1.iloc[-1]
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

        bullish_candle = (
            close > open_
        )

        higher_close = (
            close > prev_close
        )

        above_ema = (
            close >= ema
        )

        rsi_trigger = (
            rsi >= 45
        )

        macd_trigger = (
            macd >= macd_sig
        )

        trigger_score = sum([
            bullish_candle,
            higher_close,
            above_ema,
            rsi_trigger,
            macd_trigger
        ])

        # 4 از 5 شروط کافی است
        if trigger_score >= 4:

            return True, (
                "1M bullish trigger"
            )

        return False, (
            f"Waiting for 1M bullish trigger "
            f"({trigger_score}/5)"
        )

    # =====================================================
    # SELL
    # =====================================================

    bearish_candle = (
        close < open_
    )

    lower_close = (
        close < prev_close
    )

    below_ema = (
        close <= ema
    )

    rsi_trigger = (
        rsi <= 55
    )

    macd_trigger = (
        macd <= macd_sig
    )

    trigger_score = sum([
        bearish_candle,
        lower_close,
        below_ema,
        rsi_trigger,
        macd_trigger
    ])

    if trigger_score >= 4:

        return True, (
            "1M bearish trigger"
        )

    return False, (
        f"Waiting for 1M bearish trigger "
        f"({trigger_score}/5)"
    )


# =========================================================
# MAIN MTF SIGNAL
# =========================================================

def generate_mtf_signal(
    df15,
    df5,
    df1=None
):

    df15 = add_mtf_indicators(
        df15
    )

    df5 = add_mtf_indicators(
        df5
    )

    if df1 is not None:

        df1 = add_mtf_indicators(
            df1
        )

    # =====================================================
    # 15M TREND
    # =====================================================

    direction = _trend_15m(
        df15
    )

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

        reasons = [
            "15M trend confirmed"
        ]

        if not s.get(
            "pullback_price"
        ):
            reasons.append(
                "No recent 5M pullback"
            )

        elif not s.get(
            "entry_not_extended"
        ):
            reasons.append(
                "Entry too far from EMA20"
            )

        elif not (
            RSI_BUY_MIN
            <= s["rsi"]
            <= RSI_BUY_MAX
        ) and direction == "BUY":

            reasons.append(
                "5M RSI not ready"
            )

        elif not (
            RSI_SELL_MIN
            <= s["rsi"]
            <= RSI_SELL_MAX
        ) and direction == "SELL":

            reasons.append(
                "5M RSI not ready"
            )

        else:

            reasons.append(
                "5M setup not ready"
            )

        return {
            "signal": "NO SIGNAL",
            "stage": "5M",
            "trend": direction,
            "reasons": reasons,
            **s
        }

    # =====================================================
    # 5M READY
    # =====================================================

    if df1 is None:

        return {
            "signal": "NO SIGNAL",
            "stage": "1M",
            "trend": direction,
            "reasons": [
                "15M trend confirmed",
                "Recent 5M pullback detected",
                "Entry window valid",
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
                "Recent 5M pullback detected",
                "Entry window valid",
                trigger_reason
            ],
            **s
        }

    # =====================================================
    # FINAL SIGNAL
    # =====================================================

    signal = direction

    score = 80
    confidence = 80
    quality = "STRONG"

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
            "Recent 5M pullback detected",
            "Entry window valid",
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

        "pullback_time": s.get(
            "pullback_time"
        ),

        "pullback_candles_ago": s.get(
            "candles_ago"
        )
    }