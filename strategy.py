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

    elif last["RSI"] > 65:
        score -= 20
        reasons.append("RSI overbought")

    # MACD
    if last["MACD"] > last["MACD_SIGNAL"]:
        score += 20
        reasons.append("MACD bullish")
    else:
        score -= 20
        reasons.append("MACD bearish")

    # ADX strength
    if last["ADX"] >= MIN_ADX:
        score += 15
        reasons.append("Strong trend")

    confidence = min(abs(score), 100)

    signal = "NO SIGNAL"

    if score >= 40 and confidence >= MIN_CONFIDENCE:
        signal = "BUY"

    elif score <= -40 and confidence >= MIN_CONFIDENCE:
        signal = "SELL"


    return {
        "signal": signal,
        "score": score,
        "confidence": confidence,
        "reasons": reasons,
        "price": last["close"],
        "rsi": last["RSI"],
        "adx": last["ADX"],
        "atr": last["ATR"]
    }
