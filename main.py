import time
import schedule

from data_feed import get_gold_data
from indicators import add_indicators
from strategy import generate_signal
from telegram_bot import send_signal


def check_market():

    print("Checking gold market...")

    df = get_gold_data()

    if df is None:
        print("No data received")
        return

    df = add_indicators(df)

    result = generate_signal(df)

    print(result)

    if result["signal"] != "NO SIGNAL":

        message = f"""
🟡 <b>GoldPro Signal Bot</b>

📌 Signal: {result['signal']}

💰 Price: {result['price']}

📊 Confidence: {result['confidence']}%

Score: {result['score']}

RSI: {result['rsi']:.2f}
ADX: {result['adx']:.2f}
ATR: {result['atr']:.2f}
"""

        send_signal(message)


print("🟡 GoldPro Signal Bot Started")
send_signal("🟡 GoldPro Signal Bot\n\n✅ اتصال تلگرام با موفقیت برقرار شد.")

schedule.every(5).minutes.do(check_market)

check_market()

while True:
    schedule.run_pending()
    time.sleep(10)