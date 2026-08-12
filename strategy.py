from config import MIN_ADX


def generate_signal(df):

    # حداقل داده لازم
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
    prev = df.iloc[-2]

    score = 0
    reasons = []

    price = float(last["close"])
    atr = float(last["ATR"])
    rsi = float(last["RSI"])
    adx = float(last["ADX"])

    ema20 = float(last["EMA20"])
    ema50 = float(last["EMA50"])

    prev_ema20 = float(prev["EMA20"])
    prev_ema50 = float(prev["EMA50"])

    macd = float(last["MACD"])
    macd_signal = float(last["MACD_SIGNAL"])

    prev_macd = float(prev["MACD"])
    prev_macd_signal = float(prev["MACD_SIGNAL"])


    # =====================================================
    # 1. روند EMA
    # =====================================================

    bullish_trend = ema20 > ema50
    bearish_trend = ema20 < ema50

    ema_bull_cross = (
        prev_ema20 <= prev_ema50
        and ema20 > ema50
    )

    ema_bear_cross = (
        prev_ema20 >= prev_ema50
        and ema20 < ema50
    )


    # =====================================================
    # 2. MACD
    # =====================================================

    macd_bullish = macd > macd_signal
    macd_bearish = macd < macd_signal

    macd_bull_cross = (
        prev_macd <= prev_macd_signal
        and macd > macd_signal
    )

    macd_bear_cross = (
        prev_macd >= prev_macd_signal
        and macd < macd_signal
    )


    # =====================================================
    # 3. RSI
    # =====================================================

    rsi_bullish_zone = 45 <= rsi < 70
    rsi_bearish_zone = 30 < rsi <= 55


    # =====================================================
    # 4. فاصله قیمت از EMA20
    #
    # اگر قیمت خیلی از EMA20 دور شده باشد،
    # احتمال ورود در انتهای حرکت بیشتر است.
    # =====================================================

    ema_distance = abs(price - ema20)

    max_ema_distance = atr * 1.5

    price_too_far_from_ema = (
        ema_distance > max_ema_distance
    )


    # =====================================================
    # 5. شروع روند / پایان پولبک
    # =====================================================

    early_bullish = (
        bullish_trend
        and rsi_bullish_zone
        and macd_bullish
        and not price_too_far_from_ema
    )

    early_bearish = (
        bearish_trend
        and rsi_bearish_zone
        and macd_bearish
        and not price_too_far_from_ema
    )


    # =====================================================
    # امتیاز BUY
    # =====================================================

    if bullish_trend:
        score += 20
        reasons.append("EMA bullish")

    if ema_bull_cross:
        score += 20
        reasons.append("EMA bullish crossover")


    if macd_bullish:
        score += 15
        reasons.append("MACD bullish")

    if macd_bull_cross:
        score += 15
        reasons.append("MACD bullish crossover")


    if 45 <= rsi < 65:
        score += 15
        reasons.append("RSI healthy")

    elif 65 <= rsi < 70:
        score += 5
        reasons.append("RSI high")


    if adx >= MIN_ADX:
        score += 10
        reasons.append("Strong trend")


    if price_too_far_from_ema:
        score -= 25
        reasons.append("Price extended from EMA")


    # =====================================================
    # امتیاز SELL
    # =====================================================

    sell_score = 0
    sell_reasons = []

    if bearish_trend:
        sell_score += 20
        sell_reasons.append("EMA bearish")

    if ema_bear_cross:
        sell_score += 20
        sell_reasons.append(
            "EMA bearish crossover"
        )


    if macd_bearish:
        sell_score += 15
        sell_reasons.append(
            "MACD bearish"
        )

    if macd_bear_cross:
        sell_score += 15
        sell_reasons.append(
            "MACD bearish crossover"
        )


    if 35 < rsi <= 55:
        sell_score += 15
        sell_reasons.append(
            "RSI healthy"
        )

    elif 30 < rsi <= 35:
        sell_score += 5
        sell_reasons.append(
            "RSI low"
        )


    if adx >= MIN_ADX:
        sell_score += 10
        sell_reasons.append(
            "Strong trend"
        )


    if price_too_far_from_ema:
        sell_score -= 25
        sell_reasons.append(
            "Price extended from EMA"
        )


    # =====================================================
    # قوانین مهم جلوگیری از ورود دیرهنگام
    # =====================================================

    signal = "NO SIGNAL"

    # BUY ممنوع وقتی RSI >= 70
    if rsi >= 70:

        score = 0
        reasons = [
            "BUY blocked - RSI >= 70"
        ]

    # SELL ممنوع وقتی RSI <= 30
    elif rsi <= 30:

        sell_score = 0
        sell_reasons = [
            "SELL blocked - RSI <= 30"
        ]


    # BUY
    if (
        rsi < 70
        and early_bullish
        and score >= 55
        and score > sell_score
    ):

        signal = "BUY"


    # SELL
    elif (
        rsi > 30
        and early_bearish
        and sell_score >= 55
        and sell_score > score
    ):

        signal = "SELL"

        score = -sell_score
        reasons = sell_reasons


    else:

        if signal != "BUY":

            if sell_score > score:
                score = -sell_score
                reasons = sell_reasons

            elif not reasons:

                reasons = [
                    "No early trend setup"
                ]


    # =====================================================
    # Confidence
    # =====================================================

    confidence = min(
        abs(score),
        100
    )


    # =====================================================
    # کیفیت
    # =====================================================

    if confidence >= 70:
        quality = "STRONG"

    elif confidence >= 55:
        quality = "NORMAL"

    else:
        quality = "WEAK"


    # =====================================================
    # TP / SL
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
    # خروجی
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