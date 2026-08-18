import requests
import pandas as pd
from datetime import datetime, timezone

from config import TWELVE_DATA_API_KEY, TIMEFRAME, CANDLE_LIMIT

URL = "https://api.twelvedata.com/time_series"


def get_market_data(symbol, interval=None, outputsize=None):
    """Return only CLOSED OHLC candles from Twelve Data."""
    interval = interval or TIMEFRAME
    outputsize = outputsize or CANDLE_LIMIT

    if not TWELVE_DATA_API_KEY:
        print("API error: TWELVE_DATA_API_KEY is missing")
        return None

    params = {
        "symbol": symbol,
        "interval": interval,
        "outputsize": outputsize,
        "timezone": "UTC",
        "apikey": TWELVE_DATA_API_KEY,
    }

    try:
        response = requests.get(URL, params=params, timeout=30)
        data = response.json()

        if data.get("status") == "error":
            print(f"[{symbol} {interval}] API error:", data)
            return None
        if "values" not in data:
            print(f"[{symbol} {interval}] Data error:", data)
            return None

        df = pd.DataFrame(data["values"])
        df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce", utc=True)

        for column in ["open", "high", "low", "close"]:
            df[column] = pd.to_numeric(df[column], errors="coerce")
        if "volume" in df.columns:
            df["volume"] = pd.to_numeric(df["volume"], errors="coerce")

        df = df.dropna(subset=["datetime", "open", "high", "low", "close"])
        df = df.sort_values("datetime").reset_index(drop=True)
        df.rename(columns={"datetime": "time"}, inplace=True)

        # Never use the still-forming candle.
        minutes = int(interval.replace("min", "")) if interval.endswith("min") else None
        if minutes:
            cutoff = pd.Timestamp(datetime.now(timezone.utc)) - pd.Timedelta(minutes=minutes)
            df = df[df["time"] <= cutoff].reset_index(drop=True)

        if df.empty:
            print(f"[{symbol} {interval}] No CLOSED candles available")
            return None

        print(f"[{symbol} {interval}] Latest CLOSED candle: {df.iloc[-1]['time']}")
        print(f"[{symbol} {interval}] Latest CLOSED close: {df.iloc[-1]['close']}")
        return df

    except requests.RequestException as e:
        print(f"[{symbol} {interval}] Connection error:", e)
        return None
    except Exception as e:
        print(f"[{symbol} {interval}] Data error:", e)
        return None


def get_gold_data():
    return get_market_data("XAU/USD", TIMEFRAME, CANDLE_LIMIT)
