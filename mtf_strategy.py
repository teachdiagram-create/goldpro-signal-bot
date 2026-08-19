from config import MIN_ADX

# =========================================================
# GoldPro MTF Strategy v5 - 75% Filter Model
#
# 30M Trend -> 15M Confirmation -> 5M Entry
#
# هدف این نسخه:
# - جلوگیری از فیلتر شدن بیش از حد سیگنال‌ها
# - صدور سیگنال وقتی حداقل 6 فیلتر از 8 فیلتر (75%) تایید باشند
# - ثبت وضعیت تک تک فیلترها برای بررسی عملکرد واقعی
# - Support/Resistance فقط اطلاعات تحلیلی است و فیلتر اجباری نیست
# =========================================================

RSI_BUY_MIN = 35
RSI_BUY_MAX = 80
RSI_SELL_MIN = 20
RSI_SELL_MAX = 65

STRONG_ADX = 35
MAX_ENTRY_DISTANCE_ATR = 2.0
SR_LOOKBACK = 50

TOTAL_FILTERS = 8
MIN_FILTERS = 6


def _latest(df):
    return df.iloc[-1]


def add_mtf_indicators(df):
    from indicators import add_indicators
    return add_indicators(df.copy())


def _support_resistance(df):
    """Use previous candles for S/R so current candle cannot move its own level."""
    if df is None or df.empty:
        return None, None

    lookback = min(SR_LOOKBACK + 1, len(df))
    recent = df.tail(lookback).iloc[:-1]

    if recent.empty:
        return None, None

    return float(recent["low"].min()), float(recent["high"].max())


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


def _confirm_15m(df15, direction):
    last = _latest(df15)
    ema20 = float(last["EMA20"])
    ema50 = float(last["EMA50"])
    adx = float(last["ADX"])

    confirmed = (
        ema20 > ema50 if direction == "BUY" else ema20 < ema50
    ) and adx >= MIN_ADX

    return confirmed, {
        "ema20_15": ema20,
        "ema50_15": ema50,
        "adx_15": adx,
        "time_15": str(last["time"]),
    }


def _entry_5m(df5, direction):
    last = _latest(df5)
    prev = df5.iloc[-2] if len(df5) >= 2 else None

    price = float(last["close"])
    open_price = float(last["open"])
    ema20 = float(last["EMA20"])
    ema50 = float(last["EMA50"])
    rsi = float(last["RSI"])
    adx = float(last["ADX"])
    atr = float(last["ATR"])
    macd = float(last["MACD"])
    macd_signal = float(last["MACD_SIGNAL"])

    bullish = direction == "BUY"

    # 1) 5M EMA trend
    f_ema = ema20 > ema50 if bullish else ema20 < ema50

    # 2) ADX trend strength
    f_adx = adx >= MIN_ADX

    # 3) RSI: broad enough to avoid rejecting strong trends at 70+
    f_rsi = (
        RSI_BUY_MIN <= rsi <= RSI_BUY_MAX
        if bullish
        else RSI_SELL_MIN <= rsi <= RSI_SELL_MAX
    )

    # 4) MACD direction
    f_macd = macd >= macd_signal if bullish else macd <= macd_signal

    # 5) Current candle direction
    f_candle = price > open_price if bullish else price < open_price

    # 6) Momentum vs previous candle
    f_momentum = True
    if prev is not None:
        prev_close = float(prev["close"])
        f_momentum = price >= prev_close if bullish else price <= prev_close

    # 7) Entry context: price should be on the correct side of EMA20
    f_context = price >= ema20 if bullish else price <= ema20

    # 8) Not excessively extended from EMA20.
    #    This is intentionally generous (2 ATR) so strong trends can still enter.
    distance_from_ema = abs(price - ema20)
    f_not_extended = distance_from_ema <= atr * MAX_ENTRY_DISTANCE_ATR

    filters = {
        "30M Trend": True,  # supplied by caller; direction already confirms it
        "15M Confirmation": True,  # supplied by caller
        "5M EMA Trend": f_ema,
        "ADX": f_adx,
        "RSI": f_rsi,
        "MACD": f_macd,
        "5M Candle": f_candle,
        "Momentum": f_momentum,
    }

    # The entry-context and extension checks are diagnostic filters.
    # They are included in the total 8 by replacing candle/momentum only when needed.
    # To keep exactly 8 filters, use this set for scoring:
    score_filters = {
        "30M Trend": True,
        "15M Confirmation": True,
        "5M EMA Trend": f_ema,
        "ADX": f_adx,
        "RSI": f_rsi,
        "MACD": f_macd,
        "5M Candle": f_candle,
        "Entry Context": f_context and f_not_extended,
    }

    passed = sum(1 for value in score_filters.values() if value)
    confidence = round((passed / TOTAL_FILTERS) * 100, 1)

    support, resistance = _support_resistance(df5)
    distance_to_support = price - support if support is not None else None
    distance_to_resistance = resistance - price if resistance is not None else None

    near_support = (
        distance_to_support is not None and distance_to_support <= atr * 0.5
    )
    near_resistance = (
        distance_to_resistance is not None and distance_to_resistance <= atr * 0.5
    )

    # Informational breakout checks use the previous S/R levels.
    breakout_resistance = (
        resistance is not None and price > resistance
    )
    breakout_support = (
        support is not None and price < support
    )

    passed_names = [name for name, ok in score_filters.items() if ok]
    failed_names = [name for name, ok in score_filters.items() if not ok]

    reasons = [
        f"Filters: {passed}/{TOTAL_FILTERS} ({confidence:.0f}%)",
        *[f"OK: {name}" for name in passed_names],
        *[f"WAIT: {name}" for name in failed_names],
    ]

    entry_ready = passed >= MIN_FILTERS

    if passed == 8:
        quality = "VERY STRONG"
    elif passed == 7:
        quality = "STRONG"
    elif passed == 6:
        quality = "NORMAL"
    else:
        quality = "WEAK"

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
        "strong_trend": adx >= STRONG_ADX,
        "distance_from_ema": distance_from_ema,
        "entry_not_extended": f_not_extended,
        "filter_count": passed,
        "total_filters": TOTAL_FILTERS,
        "confidence": confidence,
        "quality": quality,
        "filters": score_filters,
        "reasons": reasons,
        "time": str(last["time"]),
    }


def generate_mtf_signal(df30, df15, df5):
    df30 = add_mtf_indicators(df30)
    df15 = add_mtf_indicators(df15)
    df5 = add_mtf_indicators(df5)

    direction = _trend_30m(df30)

    if direction == "NONE":
        return {
            "signal": "NO SIGNAL",
            "stage": "30M",
            "reasons": ["No 30M trend confirmation"],
        }

    confirmed, c = _confirm_15m(df15, direction)

    if not confirmed:
        return {
            "signal": "NO SIGNAL",
            "stage": "15M",
            "trend": direction,
            "reasons": [
                "30M trend confirmed",
                "15M confirmation failed",
            ],
            **c,
        }

    entry_ready, e = _entry_5m(df5, direction)

    if not entry_ready:
        return {
            "signal": "NO SIGNAL",
            "stage": "5M",
            "trend": direction,
            "reasons": [
                "30M trend confirmed",
                "15M confirmation confirmed",
                *e["reasons"],
            ],
            **c,
            **e,
        }

    signal = direction
    confidence = e["confidence"]
    score = int(round(confidence))
    quality = e["quality"]

    if signal == "BUY":
        sl = e["price"] - e["atr"] * 1.5
        tp1 = e["price"] + e["atr"] * 2
        tp2 = e["price"] + e["atr"] * 3
    else:
        sl = e["price"] + e["atr"] * 1.5
        tp1 = e["price"] - e["atr"] * 2
        tp2 = e["price"] - e["atr"] * 3

    reasons = [
        "30M trend confirmed",
        "15M confirmation confirmed",
        *e["reasons"],
    ]

    # S/R is diagnostic only in this version.
    if e["breakout_resistance"] and signal == "BUY":
        reasons.append("Resistance breakout")
    elif e["breakout_support"] and signal == "SELL":
        reasons.append("Support breakdown")
    elif e["near_resistance"]:
        reasons.append("Near resistance")
    elif e["near_support"]:
        reasons.append("Near support")

    return {
        "signal": signal,
        "score": score,
        "confidence": confidence,
        "quality": quality,
        "filter_count": e["filter_count"],
        "total_filters": e["total_filters"],
        "filters": e["filters"],
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
        "distance_to_support": e["distance_to_support"],
        "distance_to_resistance": e["distance_to_resistance"],
        "stage": "5M",
        "trend": direction,
    }
