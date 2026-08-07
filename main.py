import time
import schedule

from data_feed import get_gold_data
from indicators import add_indicators
from strategy import generate_signal
from telegram_bot import send_signal

import os

print("TWELVE_DATA_API_KEY loaded:", bool(os.getenv("TWELVE_DATA_API_KEY")))


def check_market():

    print("Checking gold market...")

from telegram_bot import send_signal
send_signal("🟡 GoldPro Bot Test - Telegram OK")


    df = get_gold_data()

    if df is None:
        print("No data received")
        return

    df = add_indicators(df)

    result = generate_signal(df)

    print(result)

    if result["signal"] != "NO SIGNAL":

        message = f"""
🟡 <b>Gold Signal</b>

📌 Signal: {result['signal']}

💰 Price: {result['price']}

🎯 Confidence: {result['confidence']}%

📊 Score: {result['score']}

RSI: {result['rsi']:.2f}
ADX: {result['adx']:.2f}
ATR: {result['atr']:.2f}
"""

        send_signal(message)


print("🟡 GoldPro Signal Bot Started")



check_market()

while True:
    schedule.run_pending()
    time.sleep(10)
