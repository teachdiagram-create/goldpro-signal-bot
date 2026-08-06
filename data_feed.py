import requests
import pandas as pd
from config import FINNHUB_API_KEY
from datetime import datetime, timedelta


def get_gold_data():
    try:
        # Finnhub Forex symbol for Gold
        symbol = "OANDA:XAU_USD"

        end = int(datetime.now().timestamp())
        start = int((datetime.now() - timedelta(hours=24)).timestamp())

        url = "https://finnhub.io/api/v1/forex/candle"

        params = {
            "symbol": symbol,
            "resolution": "5",
            "from": start,
            "to": end,
            "token": FINNHUB_API_KEY
        }

        response = requests.get(url, params=params)
        data = response.json()

        if data.get("s") != "ok":
            print("API error:", data)
            return None

        df = pd.DataFrame({
            "time": data["t"],
            "open": data["o"],
            "high": data["h"],
            "low": data["l"],
            "close": data["c"],
            "volume": data["v"]
        })

        df["time"] = pd.to_datetime(df["time"], unit="s")

        return df

    except Exception as e:
        print("Data error:", e)
        return None
