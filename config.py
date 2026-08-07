import os

# Twelve Data
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")

# Telegram
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# Gold
SYMBOL = "XAU/USD"
TIMEFRAME = "5min"
CANDLE_LIMIT = 200

# Indicators
EMA_FAST = 20
EMA_SLOW = 50
RSI_PERIOD = 14
ADX_PERIOD = 14
ATR_PERIOD = 14

# Signal settings
MIN_CONFIDENCE = 60
MIN_ADX = 20