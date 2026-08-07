import requests
import pandas as pd

from config import TWELVE_DATA_API_KEY, SYMBOL, TIMEFRAME, CANDLE_LIMIT


def get_gold_data():

    if not TWELVE_DATA_API_KEY:
        print("API error: TWELVE_DATA_API_KEY is missing")
        return None

    url = "https://api.twelvedata.com/time_series"

    params = {
        "symbol": SYMBOL,
        "interval": TIMEFRAME,
        "outputsize": CANDLE_LIMIT,
        "apikey": TWELVE_DATA_API_KEY
    }

    try:
        response = requests.get(url, params=params, timeout=30)

        data = response.json()

        if "status" in data and data["status"] == "error":
            print("API error:", data)
            return None

        if "values" not in data:
            print("Data error:", data)
            return None

        df = pd.DataFrame(data["values"])

        df["datetime"] = pd.to_datetime(df["datetime"])

        for column in ["open", "high", "low", "close"]:
            df[column] = pd.to_numeric(df[column], errors="coerce")

        if "volume" in df.columns:
            df["volume"] = pd.to_numeric(
                df["volume"],
                errors="coerce"
            )

        df = df.sort_values("datetime").reset_index(drop=True)

        df.rename(
            columns={"datetime": "time"},
            inplace=True
        )

        return df

    except requests.RequestException as e:
        print("Connection error:", e)
        return None

    except Exception as e:
        print("Data error:", e)
        return None