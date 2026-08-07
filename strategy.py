from config import MIN_CONFIDENCE, MIN_ADX


def generate_signal(df):

    last = df.iloc[-1]

    score = 0
    reasons = []

    # EMA Trend
    if last["EMA20"] > last["EMA50"]:
        score += 25
        reasons.append("EMA bullish")
    else:
        score -= 25
        reasons.append("EMA bearish")


    # RSI
    if last["RSI"] < 35:
        score += 20
        reasons.append("RSI oversold")

    elif last["RSI"] > 70:
        score -= 10
        reasons.append("RSI overbought")


    # MACD
    if last["MACD"] > last["MACD_SIGNAL"]:
        score += 20
        reasons.append("MACD bullish")
    else:
        score -= 20
        reasons.append("MACD bearish")


    # ADX
    if last["ADX"] >= MIN_ADX:
        score += 15
        reasons.append("Strong trend")


    confidence = min(abs(score), 100)


    signal = "NO SIGNAL"

    if score >= 50 and confidence >= MIN_CONFIDENCE:
        signal = "BUY"

    elif score <= -50 and confidence >= MIN_CONFIDENCE:
        signal = "SELL"


    price = float(last["close"])
    atr = float(last["ATR"])


    if signal == "BUY":

        sl = price - (atr * 1.5)
        tp1 = price + (atr * 2)
        tp2 = price + (atr * 3)

    elif signal == "SELL":

        sl = price + (atr * 1.5)
        tp1 = price - (atr * 2)
        tp2 = price - (atr * 3)

    else:

        sl = None
        tp1 = None
        tp2 = None


    if confidence >= 75:
        quality = "VERY STRONG"

    elif confidence >= 60:
        quality = "STRONG"

    elif confidence >= 50:
        quality = "NORMAL"

    else:
        quality = "WEAK"


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
        "rsi": float(last["RSI"]),
        "adx": float(last["ADX"]),
        "atr": atr
    }