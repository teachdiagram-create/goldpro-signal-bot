import ta


def add_indicators(df):

    # EMA
    df["EMA20"] = ta.trend.ema_indicator(
        df["close"],
        window=20
    )

    df["EMA50"] = ta.trend.ema_indicator(
        df["close"],
        window=50
    )

    # RSI
    df["RSI"] = ta.momentum.rsi(
        df["close"],
        window=14
    )

    # MACD
    macd = ta.trend.MACD(
        df["close"],
        window_fast=12,
        window_slow=26,
        window_sign=9
    )

    df["MACD"] = macd.macd()
    df["MACD_SIGNAL"] = macd.macd_signal()

    # ADX
    df["ADX"] = ta.trend.adx(
        df["high"],
        df["low"],
        df["close"],
        window=14
    )

    # ATR
    df["ATR"] = ta.volatility.average_true_range(
        df["high"],
        df["low"],
        df["close"],
        window=14
    )

    return df
