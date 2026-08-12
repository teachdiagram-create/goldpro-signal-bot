from config import MIN_ADX


def generate_signal(df):

    last = df.iloc[-1]
    previous = df.iloc[-2]

    score = 0
    reasons = []

    # =====================================================
    # EMA Trend
    # =====================================================

    ema_bullish = last["EMA20"] > last["EMA50"]

    if ema_bullish:
        score += 25
        reasons.append("EMA bullish")
    else:
        score -= 25
        reasons.append("EMA bearish")

    # =====================================================
    # RSI
    # =====================================================

    rsi = float(last["RSI"])
    previous_rsi = float(previous["RSI"])

    rsi_rising = rsi > previous_rsi

    if rsi < 35:

        score += 20
        reasons.append("RSI oversold")

    elif rsi > 75:

        score -= 15
        reasons.append("RSI overbought")

    elif 50 <= rsi <= 70:

        score += 10

        if rsi_rising:
            reasons.append("RSI bullish momentum")
        else:
            reasons.append("RSI neutral")

    # =====================================================
    # MACD
    # =====================================================

    macd_bullish = (
        last["MACD"] > last["MACD_SIGNAL"]
    )

    if macd_bullish:

        score += 20
        reasons.append("MACD bullish")

    else:

        score -= 20
        reasons.append("MACD bearish")

    # =====================================================
    # ADX
    # =====================================================

    adx = float(last["ADX"])

    if adx >= MIN_ADX:

        score += 15
        reasons.append("Strong trend")

    # =====================================================
    # Confidence
    # =====================================================

    confidence = min(
        abs(score),
        100
    )

    # =====================================================
    # Signal
    # =====================================================

    signal = "NO SIGNAL"

    # -----------------------------------------------------
    # BUY FILTER
    # RSI بالای 70 اجازه BUY ندارد
    # -----------------------------------------------------

    buy_allowed = (
        rsi <= 70
        and rsi_rising
    )

    if (
        score >= 40
        and confidence >= 50
        and buy_allowed
    ):

        signal = "BUY"

    elif (
        score <= -40
        and confidence >= 50
    ):

        signal = "SELL"

    # =====================================================
    # Price / ATR
    # =====================================================

    price = float(last["close"])
    atr = float(last["ATR"])

    sl = None
    tp1 = None
    tp2 = None

    # =====================================================
    # BUY
    # =====================================================

    if signal == "BUY":

        sl = price - (atr * 1.5)

        tp1 = price + (atr * 2)

        tp2 = price + (atr * 3)

    # =====================================================
    # SELL
    # =====================================================

    elif signal == "SELL":

        sl = price + (atr * 1.5)

        tp1 = price - (atr * 2)

        tp2 = price - (atr * 3)

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
    # Return
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