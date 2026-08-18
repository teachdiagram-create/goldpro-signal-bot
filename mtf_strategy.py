from config import MIN_ADX

# =========================================================
# GoldPro MTF Early Entry Strategy
# 15M Trend → 5M Pullback / Momentum → 1M Trigger
# =========================================================

RSI_BUY_MIN = 38
RSI_BUY_MAX = 68

RSI_SELL_MIN = 32
RSI_SELL_MAX = 62

# فاصله قابل قبول از EMA20 بر اساس ATR
NORMAL_PULLBACK_ATR = 0.75
EARLY_ENTRY_ATR = 1.50

# برای جلوگیری از ورود خیلی دیر
MAX_EXTENSION_ATR = 2.00


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
# 5M SETUP
# =========================================================

def _setup_5m(df5, direction):

    last = _latest(df5)

    prev = df5.iloc[-2] if len(df5) >= 2 else None

    price = float(last["close"])
    ema20 = float(last["EMA20"])
    ema50 = float(last["EMA50"])
    rsi = float(last["RSI"])
    adx = float(last["ADX"])
    atr = float(last["ATR"])
    macd = float(last["MACD"])
    macd_signal = float(last["MACD_SIGNAL"])

    distance_from_ema = abs(price - ema20)

    # =====================================================
    # BUY
    # =====================================================

    if direction == "BUY":

        trend_ok = ema20 > ema50

        rsi_ok = RSI_BUY_MIN <= rsi <= RSI_BUY_MAX

        macd_ok = macd >= macd_signal

        # Pullback معمولی
        normal_pullback = (
            distance_from_ema <= atr * NORMAL_PULLBACK_ATR
        )

        # ورود زودتر در شروع حرکت
        early_entry = (
            distance_from_ema <= atr * EARLY_ENTRY_ATR
            and rsi >= 42
        )

        momentum_recovery = False

        if prev is not None:

            previous_macd = float(prev["MACD"])
            previous_signal = float(prev["MACD_SIGNAL"])

            previous_diff = (
                previous_macd - previous_signal
            )

            current_diff = (
                macd - macd_signal
            )

            if current_diff > previous_diff:
                momentum_recovery = True

        setup = (
            trend_ok
            and adx >= MIN_ADX
            and rsi_ok
            and (
                normal_pullback
                or early_entry
            )
            and (
                macd_ok
                or momentum_recovery
            )
        )

    # =====================================================
    # SELL
    # =====================================================

    else:

        trend_ok = ema20 < ema50

        rsi_ok = RSI_SELL_MIN <= rsi <= RSI_SELL_MAX

        macd_ok = macd <= macd_signal

        # Pullback معمولی
        normal_pullback = (
            distance_from_ema <= atr * NORMAL_PULLBACK_ATR
        )

        # -------------------------------------------------
        # Early SELL
        #
        # اگر روند قوی نزولی باشد، اجازه می‌دهیم
        # کمی دورتر از EMA20 هم وارد شویم.
        # -------------------------------------------------

        strong_sell_momentum = (
            macd < macd_signal
            and adx >= MIN_ADX
        )

        early_entry = (
            distance_from_ema <= atr * EARLY_ENTRY_ATR
            and (
                rsi >= 35
                or strong_sell_momentum
            )
        )

        # اگر RSI بیش از حد oversold شده،
        # ورود خیلی دیر را قبول نمی‌کنیم.
        not_extreme = rsi >= 28

        setup = (
            trend_ok
            and adx >= MIN_ADX
            and rsi_ok
            and not_extreme
            and (
                normal_pullback
                or early_entry
            )
            and macd_ok
        )

    # =====================================================
    # اطلاعات تشخیصی
    # =====================================================

    entry_not_extended = (
        distance_from_ema <= atr * MAX_EXTENSION_ATR
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

        "time": str(last["time"]),

        "distance_from_ema": distance_from_ema,

        "entry_not_extended": entry_not_extended
    }


# =========================================================
# 1M TRIGGER
# =========================================================

def _trigger_1m(df1, direction):

    if df1 is None or len(df1) < 3:

        return False, "Not enough 1M candles"

    last = _latest(df1)

    prev = df1.iloc[-2]

    close = float(last["close"])

    open_ = float(last["open"])

    prev_close = float(prev["close"])

    ema = float(last["EMA20"])

    rsi = float(last["RSI"])

    macd = float(last["MACD"])

    macd_sig = float(last["MACD_SIGNAL"])

    # =====================================================
    # BUY TRIGGER
    # =====================================================

    if direction == "BUY":

        bullish_candle = close > open_

        higher_close = close > prev_close

        above_ema = close >= ema

        rsi_trigger = rsi >= 43

        macd_trigger = macd >= macd_sig

        trigger = (
            bullish_candle
            and higher_close
            and above_ema
            and rsi_trigger
            and macd_trigger
        )

        if trigger:

            return True, "1M bullish trigger"

        return False, "Waiting for 1M bullish trigger"

    # =====================================================
    # SELL TRIGGER
    # =====================================================

    bearish_candle = close < open_

    lower_close = close < prev_close

    below_ema = close <= ema

    rsi_trigger = rsi <= 57

    macd_trigger = macd <= macd_sig

    trigger = (
        bearish_candle
        and lower_close
        and below_ema
        and rsi_trigger
        and macd_trigger
    )

    if trigger:

        return True, "1M bearish trigger"

    return False, "Waiting for 1M bearish trigger"


# =========================================================
# MAIN MTF SIGNAL
# =========================================================

def generate_mtf_signal(df15, df5, df1=None):

    df15 = add_mtf_indicators(df15)

    df5 = add_mtf_indicators(df5)

    if df1 is not None:

        df1 = add_mtf_indicators(df1)

    # =====================================================
    # 15M TREND
    # =====================================================

    direction = _trend_15m(df15)

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

        return {

            "signal": "NO SIGNAL",

            "stage": "5M",

            "trend": direction,

            "reasons": [
                "15M trend confirmed",
                "No 5M early-entry setup"
            ],

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
                "5M early-entry setup ready",
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

   