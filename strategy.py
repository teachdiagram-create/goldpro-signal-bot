from config import MIN_ADX


# =========================================================
# GoldPro Early Entry Strategy
# =========================================================

RSI_MIN = 40
RSI_MAX = 65

EARLY_RSI_MIN = 42
EARLY_RSI_MAX = 62

MIN_CONFIDENCE = 50


def generate_signal(df):

    last = df.iloc[-1]

    # -----------------------------------------------------
    # مقدارهای فعلی
    # -----------------------------------------------------

    ema20 = float(last["EMA20"])
    ema50 = float(last["EMA50"])

    rsi = float(last["RSI"])

    macd = float(last["MACD"])
    macd_signal = float(last["MACD_SIGNAL"])

    adx = float(last["ADX"])
    atr = float(last["ATR"])

    price = float(last["close"])

    score = 0
    reasons = []

    # -----------------------------------------------------
    # کندل قبلی برای تشخیص تغییر مومنتوم
    # -----------------------------------------------------

    previous = None

    if len(df) >= 2:
        previous = df.iloc[-2]

    # =====================================================
    # EMA TREND
    # =====================================================

    ema_bullish = ema20 > ema50
    ema_bearish = ema20 < ema50

    if ema_bullish:

        score += 25

        reasons.append(
            "EMA bullish"
        )

    elif ema_bearish:

        score -= 25

        reasons.append(
            "EMA bearish"
        )

    # =====================================================
    # RSI
    # =====================================================

    rsi_healthy = (
        RSI_MIN <= rsi <= RSI_MAX
    )

    rsi_recovery = False
    rsi_falling = False

    if previous is not None:

        previous_rsi = float(
            previous["RSI"]
        )

        # RSI در حال برگشت از ناحیه پایین
        if (
            previous_rsi < rsi
            and rsi >= EARLY_RSI_MIN
            and rsi <= EARLY_RSI_MAX
        ):

            rsi_recovery = True

        # RSI در حال برگشت از ناحیه بالا
        if (
            previous_rsi > rsi
            and rsi >= EARLY_RSI_MIN
            and rsi <= EARLY_RSI_MAX
        ):

            rsi_falling = True

    # -----------------------------------------------------
    # RSI اصلی
    # -----------------------------------------------------

    if rsi_healthy:

        score += 20

        reasons.append(
            "RSI healthy"
        )

    elif rsi > RSI_MAX:

        score -= 20

        reasons.append(
            "RSI too high"
        )

    elif rsi < RSI_MIN:

        score -= 20

        reasons.append(
            "RSI too low"
        )

    # =====================================================
    # MACD
    # =====================================================

    macd_bullish = (
        macd > macd_signal
    )

    macd_bearish = (
        macd < macd_signal
    )

    macd_recovery = False
    macd_falling = False

    if previous is not None:

        previous_macd = float(
            previous["MACD"]
        )

        previous_signal = float(
            previous["MACD_SIGNAL"]
        )

        previous_diff = (
            previous_macd
            - previous_signal
        )

        current_diff = (
            macd
            - macd_signal
        )

        # MACD در حال نزدیک شدن به کراس صعودی
        if (
            current_diff > previous_diff
            and current_diff < 0
        ):

            macd_recovery = True

        # MACD در حال نزدیک شدن به کراس نزولی
        if (
            current_diff < previous_diff
            and current_diff > 0
        ):

            macd_falling = True

    if macd_bullish:

        score += 20

        reasons.append(
            "MACD bullish"
        )

    elif macd_bearish:

        score -= 20

        reasons.append(
            "MACD bearish"
        )

    # =====================================================
    # ADX
    # =====================================================

    strong_trend = (
        adx >= MIN_ADX
    )

    if strong_trend:

        score += 15

        reasons.append(
            "Strong trend"
        )

    # =====================================================
    # EARLY MOMENTUM RECOVERY
    # =====================================================

    early_buy = False
    early_sell = False

    # -----------------------------------------------------
    # Early BUY
    #
    # EMA bullish
    # RSI healthy
    # MACD هنوز bearish است اما در حال recovery
    # -----------------------------------------------------

    if (
        ema_bullish
        and rsi_healthy
        and macd_recovery
        and strong_trend
        and RSI_MIN <= rsi <= RSI_MAX
    ):

        early_buy = True

        score += 25

        reasons.append(
            "Early momentum recovery"
        )

    # -----------------------------------------------------
    # Early SELL
    #
    # EMA bearish
    # RSI healthy
    # MACD هنوز bullish است اما در حال weakening
    # -----------------------------------------------------

    if (
        ema_bearish
        and rsi_healthy
        and macd_falling
        and strong_trend
        and RSI_MIN <= rsi <= RSI_MAX
    ):

        early_sell = True

        score -= 25

        reasons.append(
            "Early momentum weakening"
        )

    # =====================================================
    # SIGNAL
    # =====================================================

    signal = "NO SIGNAL"

    confidence = min(
        abs(score),
        100
    )

    # -----------------------------------------------------
    # BUY
    # -----------------------------------------------------

    if (
        ema_bullish
        and rsi_healthy
        and strong_trend
        and (
            macd_bullish
            or early_buy
        )
        and score >= 40
        and confidence >= MIN_CONFIDENCE
    ):

        signal = "BUY"

    # -----------------------------------------------------
    # SELL
    # -----------------------------------------------------

    elif (
        ema_bearish
        and rsi_healthy
        and strong_trend
        and (
            macd_bearish
            or early_sell
        )
        and score <= -40
        and confidence >= MIN_CONFIDENCE
    ):

        signal = "SELL"

    # =====================================================
    # QUALITY
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