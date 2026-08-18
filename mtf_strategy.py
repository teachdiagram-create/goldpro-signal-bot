from config import MIN_ADX

RSI_MIN = 40
RSI_MAX = 65


def _latest(df):
    return df.iloc[-1]


def add_mtf_indicators(df):
    from indicators import add_indicators
    return add_indicators(df.copy())


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

    if direction == "BUY":
        trend_ok = ema20 > ema50
        rsi_ok = RSI_MIN <= rsi <= RSI_MAX
        momentum_ok = macd >= macd_signal or (prev is not None and macd > float(prev["MACD"]))
        pullback = price <= ema20 + atr * 0.45
        not_extended = price <= ema20 + atr * 1.0
    else:
        trend_ok = ema20 < ema50
        rsi_ok = RSI_MIN <= rsi <= RSI_MAX
        momentum_ok = macd <= macd_signal or (prev is not None and macd < float(prev["MACD"]))
        pullback = price >= ema20 - atr * 0.45
        not_extended = price >= ema20 - atr * 1.0

    setup = trend_ok and rsi_ok and adx >= MIN_ADX and momentum_ok and pullback and not_extended
    return setup, {
        "price": price, "rsi": rsi, "adx": adx, "atr": atr,
        "ema20": ema20, "ema50": ema50, "macd": macd,
        "macd_signal": macd_signal, "time": str(last["time"])
    }


def _trigger_1m(df1, direction):
    if df1 is None or len(df1) < 3:
        return False, "Not enough 1M candles"

    last = _latest(df1)
    prev = df1.iloc[-2]

    close = float(last["close"])
    open_ = float(last["open"])
    prev_close = float(prev["close"])
    prev_open = float(prev["open"])
    ema = float(last["EMA20"])
    rsi = float(last["RSI"])
    macd = float(last["MACD"])
    macd_sig = float(last["MACD_SIGNAL"])

    if direction == "BUY":
        trigger = close > open_ and close > prev_close and close >= ema and rsi >= 45 and macd >= macd_sig
        return trigger, "1M bullish trigger" if trigger else "Waiting for 1M bullish trigger"
    trigger = close < open_ and close < prev_close and close <= ema and rsi <= 55 and macd <= macd_sig
    return trigger, "1M bearish trigger" if trigger else "Waiting for 1M bearish trigger"


def generate_mtf_signal(df15, df5, df1=None):
    df15 = add_mtf_indicators(df15)
    df5 = add_mtf_indicators(df5)
    if df1 is not None:
        df1 = add_mtf_indicators(df1)

    direction = _trend_15m(df15)
    if direction == "NONE":
        return {"signal": "NO SIGNAL", "stage": "15M", "reasons": ["No 15M trend confirmation"]}

    setup, s = _setup_5m(df5, direction)
    if not setup:
        return {
            "signal": "NO SIGNAL", "stage": "5M", "trend": direction,
            "reasons": ["15M trend confirmed", "5M setup not ready"], **s
        }

    if df1 is None:
        return {
            "signal": "NO SIGNAL", "stage": "1M", "trend": direction,
            "reasons": ["15M trend confirmed", "5M setup ready", "Waiting for 1M trigger"], **s
        }

    trigger, trigger_reason = _trigger_1m(df1, direction)
    if not trigger:
        return {
            "signal": "NO SIGNAL", "stage": "1M", "trend": direction,
            "reasons": ["15M trend confirmed", "5M setup ready", trigger_reason], **s
        }

    score = 80
    quality = "STRONG"
    signal = direction
    if direction == "BUY":
        sl = s["price"] - s["atr"] * 1.5
        tp1 = s["price"] + s["atr"] * 2
        tp2 = s["price"] + s["atr"] * 3
    else:
        sl = s["price"] + s["atr"] * 1.5
        tp1 = s["price"] - s["atr"] * 2
        tp2 = s["price"] - s["atr"] * 3

    return {
        "signal": signal, "score": score, "confidence": score,
        "quality": quality,
        "reasons": ["15M trend confirmed", "5M pullback setup", trigger_reason],
        "price": s["price"], "sl": sl, "tp1": tp1, "tp2": tp2,
        "rsi": s["rsi"], "adx": s["adx"], "atr": s["atr"],
        "stage": "1M", "trend": direction
    }
