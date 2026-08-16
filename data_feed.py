import requests
import pandas as pd

from config import TWELVE_DATA_API_KEY, TIMEFRAME, CANDLE_LIMIT


def get_live_price(symbol):
    """Get current/live price from Twelve Data."""

    if not TWELVE_DATA_API_KEY:
        print(f"[{symbol}] API error: TWELVE_DATA_API_KEY is missing")
        return None

    url = "https://api.twelvedata.com/price"

    params = {
        "symbol": symbol,
        "apikey": TWELVE_DATA_API_KEY,
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        data = response.json()

        if data.get("status") == "error":
            print(f"[{symbol}] Live price API error:", data)
            return None

        if "price" not in data:
            print(f"[{symbol}] Live price data error:", data)
            return None

        price = float(data["price"])

        print(f"[{symbol}] 🔴 LIVE API PRICE: {price}")

        return price

    except requests.RequestException as e:
        print(f"[{symbol}] Live price connection error:", e)
        return None

    except Exception as e:
        print(f"[{symbol}] Live price error:", e)
        return None


def get_market_data(symbol):
    """Get OHLC candles for one market from Twelve Data."""

    if not TWELVE_DATA_API_KEY:
        print("API error: TWELVE_DATA_API_KEY is missing")
        return None

    url = "https://api.twelvedata.com/time_series"

    params = {
        "symbol": symbol,
        "interval": TIMEFRAME,
        "outputsize": CANDLE_LIMIT,
        "apikey": TWELVE_DATA_API_KEY,
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        data = response.json()

        if data.get("status") == "error":
            print(f"[{symbol}] API error:", data)
            return None

        if "values" not in data:
            print(f"[{symbol}] Data error:", data)
            return None

        df = pd.DataFrame(data["values"])

        df["datetime"] = pd.to_datetime(
            df["datetime"],
            errors="coerce"
        )

        for column in ["open", "high", "low", "close"]:
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            )

        if "volume" in df.columns:
            df["volume"] = pd.to_numeric(
                df["volume"],
                errors="coerce"
            )

        df = df.dropna(
            subset=[
                "datetime",
                "open",
                "high",
                "low",
                "close"
            ]
        )

        df = df.sort_values(
            "datetime"
        ).reset_index(drop=True)

        df.rename(
            columns={"datetime": "time"},
            inplace=True
        )

        if df.empty:
            return None

        # Live price
        live_price = get_live_price(symbol)

        print(
            f"[{symbol}] Latest candle: "
            f"{df.iloc[-1]['time']}"
        )

        print(
            f"[{symbol}] Latest candle close: "
            f"{df.iloc[-1]['close']}"
        )

        if live_price is not None:
            print(
                f"[{symbol}] 📊 LIVE vs CANDLE: "
                f"{live_price} vs "
                f"{df.iloc[-1]['close']}"
            )

        return df

    except requests.RequestException as e:
        print(f"[{symbol}] Connection error:", e)
        return None

    except Exception as e:
        print(f"[{symbol}] Data error:", e)
        return None


# Backward compatibility
def get_gold_data():
    return get_market_data("XAU/USD")