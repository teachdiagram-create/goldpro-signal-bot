from config import MIN_ADX


# =========================================================
# GoldPro Early Trend Strategy
# =========================================================

RSI_MIN = 40
RSI_MAX = 65

EMA_SCORE = 25
RSI_SCORE = 20
MACD_SCORE = 20
ADX_SCORE = 15
MOMENTUM_SCORE = 20


def generate_signal(df):

    if df is None or len(df) < 3:
        return {
            "signal": "NO SIGNAL",
            "score": 0,
            "confidence": 0,
            "quality": "WEAK",
            "reasons": ["Not enough data"],
            "price": None,
            "sl": None,
            "tp1": None,
            "tp2": None,
            "rsi": None,
            "adx": None,
            "atr": None
        }

    last = df.iloc[-1]
    previous = df.iloc[-2]

    score = 0
    reasons = []

    # =====================================================
    # Indicators
    # =====================================================

    ema20 = float(last["EMA20"])
    ema50 = float(last["EMA50"])

    rsi = float(last["RSI"])
    previous_rsi = float(previous["RSI"])

    macd = float(last["MACD"])
    macd_signal = float(last["MACD_SIGNAL"])

    previous_macd = float(previous["MACD"])
    previous_macd_signal = float(previous["MACD_SIGNAL"])

    adx = float(last["ADX"])
    price = float(last["close"])
    previous_close = float(previous["close"])

    atr = float(last["ATR"])

    # =====================================================
    # TREND
    # =====================================================

    bullish_trend = ema20 > ema50
    bearish_trend = ema20 < ema50

    if bullish_trend:

        score += EMA_SCORE
        reasons.append("EMA bullish")

    elif bearish_trend:

        score -= EMA_SCORE
        reasons.append("EMA bearish")

    # =====================================================
    # RSI
    # =====================================================

    rsi_healthy = (
        RSI_MIN <= rsi <= RSI_MAX
    )

    if rsi_healthy:

        if bullish_trend:

            score += RSI_SCORE
            reasons.append("RSI healthy")

        elif bearish_trend:

            score -= RSI_SCORE
            reasons.append("RSI healthy")

    elif rsi > RSI_MAX:

        reasons.append("RSI too high")

    elif rsi < RSI_MIN:

        reasons.append("RSI too low")

    # =====================================================
    # MACD
    # =====================================================

    macd_bullish = macd > macd_signal
    macd_bearish = macd < macd_signal

    if macd_bullish:

        score += MACD_SCORE
        reasons.append("MACD bullish")

    elif macd_bearish:

        score -= MACD_SCORE
        reasons.append("MACD bearish")

    # =====================================================
    # ADX
    # =====================================================

    strong_trend = (
        adx >= MIN_ADX
    )

    if strong_trend:

        if bullish_trend:

            score += ADX_SCORE

        elif bearish_trend:

            score -= ADX_SCORE

        reasons.append("Strong trend")

    # =====================================================
    # PULLBACK DETECTION
    # =====================================================

    pullback_buy = (
        bullish_trend
        and previous_close < ema20
        and price >= ema20
    )

    pullback_sell = (
        bearish_trend
        and previous_close > ema20
        and price <= ema20
    )

    if pullback_buy:

        reasons.append(
            "Pullback detected"
        )

    elif pullback_sell:

        reasons.append(
            "Pullback detected"
        )

    # =====================================================
    # EARLY MOMENTUM RECOVERY
    # =====================================================

    momentum_recovery_buy = (
        bullish_trend
        and rsi > previous_rsi
        and macd > previous_macd
    )

    momentum_recovery_sell = (
        bearish_trend
        and rsi < previous_rsi
        and macd < previous_macd
    )

    if momentum_recovery_buy:

        score += MOMENTUM_SCORE

        reasons.append(
            "Early momentum recovery"
        )

    elif momentum_recovery_sell:

        score -= MOMENTUM_SCORE

        reasons.append(
            "Early momentum recovery"
        )

    # =====================================================
    # SIGNAL FILTER
    # =====================================================

    signal = "NO SIGNAL"

    # BUY
    if (
        bullish_trend
        and rsi_healthy
        and macd_bullish
        and strong_trend
        and (
            pullback_buy
            or momentum_recovery_buy
        )
        and score >= 50
    ):

        signal = "BUY"

    # SELL
    elif (
        bearish_trend
        and rsi_healthy
        and macd_bearish
        and strong_trend
        and (
            pullback_sell
            or momentum_recovery_sell
        )
        and score <= -50
    ):

        signal = "SELL"

    # =====================================================
    # Confidence
    # =====================================================

    confidence = min(
        abs(score),
        100
    )

    # =====================================================
    # Quality
    # =====================================================

    if confidence >= 70:

        quality = "STRONG"

    elif confidence >= 50:

        quality = "NORMAL"

    else:

        quality = "WEAK"

    # =====================================================
    # SL / TP
    # =====================================================

    sl = None
    tp1 = None
    tp2 = None

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

    elif signal == "SELL":

        sl = price + (
            atr * 1.5
        )

        tp1 = price - (
            atr * 2
        )

        tp2 = price - (
            atr * 3
        )

    # =====================================================
    # RESULT
    # =====================================================

    return {

        "signal": signal,

        "score": score,

        "confidence": confidence,

        "quality": quality,

        "reasons": reasons,

        "price": price,

        "sl": sl,

        "tp1": tp1,

        "tp2": tp2,

        "rsi": rsi,

        "adx": adx,

        "atr": atr
    }