from config import MIN_ADX


# =========================================================
# تنظیمات استراتژی Pullback
# =========================================================

RSI_BUY_MIN = 40
RSI_BUY_MAX = 65

RSI_SELL_MIN = 35
RSI_SELL_MAX = 60

PULLBACK_LOOKBACK = 3

# حداکثر فاصله قیمت از EMA20 بر اساس ATR
MAX_EMA_DISTANCE_ATR = 1.0


# =========================================================
# Generate Signal
# =========================================================

def generate_signal(df):

    if df is None or len(df) < 5:

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

    score = 0
    reasons = []

    price = float(last["close"])
    atr = float(last["ATR"])

    ema20 = float(last["EMA20"])
    ema50 = float(last["EMA50"])

    rsi = float(last["RSI"])
    adx = float(last["ADX"])

    macd = float(last["MACD"])
    macd_signal = float(last["MACD_SIGNAL"])

    # =====================================================
    # بررسی Pullback در 3 کندل اخیر
    # =====================================================

    recent = df.tail(
        PULLBACK_LOOKBACK
    )

    pullback_buy = False
    pullback_sell = False

    # ---------------------------------------------
    # BUY Pullback
    # ---------------------------------------------

    for _, candle in recent.iterrows():

        candle_low = float(candle["low"])
        candle_high = float(candle["high"])
        candle_ema20 = float(candle["EMA20"])
        candle_atr = float(candle["ATR"])

        # قیمت در محدوده EMA20 قرار گرفته
        if abs(
            candle_low - candle_ema20
        ) <= candle_atr * 0.7:

            pullback_buy = True

        # -----------------------------------------
        # SELL Pullback
        # -----------------------------------------

        if abs(
            candle_high - candle_ema20
        ) <= candle_atr * 0.7:

            pullback_sell = True


    # =====================================================
    # فاصله قیمت فعلی از EMA20
    # =====================================================

    ema_distance = abs(
        price - ema20
    )

    price_near_ema = (
        ema_distance
        <= atr * MAX_EMA_DISTANCE_ATR
    )


    # =====================================================
    # کندل فعلی
    # =====================================================

    current_open = float(
        last["open"]
    )

    current_close = float(
        last["close"]
    )

    current_high = float(
        last["high"]
    )

    current_low = float(
        last["low"]
    )


    current_bullish = (
        current_close > current_open
    )

    current_bearish = (
        current_close < current_open
    )


    # =====================================================
    # کندل قبلی
    # =====================================================

    previous = df.iloc[-2]

    previous_high = float(
        previous["high"]
    )

    previous_low = float(
        previous["low"]
    )


    # =====================================================
    # BUY CONDITIONS
    # =====================================================

    buy_conditions = [

        # روند صعودی
        ema20 > ema50,

        # RSI سالم
        RSI_BUY_MIN <= rsi <= RSI_BUY_MAX,

        # MACD صعودی
        macd > macd_signal,

        # روند دارای قدرت
        adx >= MIN_ADX,

        # پولبک اتفاق افتاده
        pullback_buy,

        # قیمت بیش از حد از EMA20 دور نشده
        price_near_ema,

        # کندل فعلی صعودی
        current_bullish,

        # برگشت مومنتوم
        current_close > previous_high
    ]


    # =====================================================
    # SELL CONDITIONS
    # =====================================================

    sell_conditions = [

        # روند نزولی
        ema20 < ema50,

        # RSI سالم
        RSI_SELL_MIN <= rsi <= RSI_SELL_MAX,

        # MACD نزولی
        macd < macd_signal,

        # روند دارای قدرت
        adx >= MIN_ADX,

        # پولبک اتفاق افتاده
        pullback_sell,

        # قیمت بیش از حد از EMA20 دور نشده
        price_near_ema,

        # کندل فعلی نزولی
        current_bearish,

        # برگشت مومنتوم
        current_close < previous_low
    ]


    # =====================================================
    # BUY SCORE
    # =====================================================

    if all(buy_conditions):

        score = 100

        reasons = [

            "EMA bullish",
            "RSI healthy",
            "MACD bullish",
            "Strong trend",
            "Pullback detected",
            "Early momentum recovery"
        ]

        signal = "BUY"


    # =====================================================
    # SELL SCORE
    # =====================================================

    elif all(sell_conditions):

        score = -100

        reasons = [

            "EMA bearish",
            "RSI healthy",
            "MACD bearish",
            "Strong trend",
            "Pullback detected",
            "Early momentum recovery"
        ]

        signal = "SELL"


    # =====================================================
    # NO SIGNAL
    # =====================================================

    else:

        signal = "NO SIGNAL"

        # برای نمایش دلیل اصلی
        if ema20 > ema50:

            reasons.append(
                "EMA bullish"
            )

        elif ema20 < ema50:

            reasons.append(
                "EMA bearish"
            )

        if RSI_BUY_MIN <= rsi <= RSI_BUY_MAX:

            reasons.append(
                "RSI healthy"
            )

        elif rsi > 65:

            reasons.append(
                "RSI too high"
            )

        elif rsi < 40:

            reasons.append(
                "RSI too low"
            )

        if macd > macd_signal:

            reasons.append(
                "MACD bullish"
            )

        else:

            reasons.append(
                "MACD bearish"
            )

        if adx >= MIN_ADX:

            reasons.append(
                "Strong trend"
            )

        if pullback_buy or pullback_sell:

            reasons.append(
                "Pullback detected"
            )

        if not price_near_ema:

            reasons.append(
                "Price too far from EMA20"
            )


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

    if confidence >= 80:

        quality = "STRONG"

    elif confidence >= 60:

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
    # Result
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