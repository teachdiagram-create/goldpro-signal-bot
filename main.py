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
        send_signal(
            "🟡 GoldPro Bot\n\n❌ No market data received"
        )
        return


    df = add_indicators(df)

    result = generate_signal(df)

    print(result)


    if result["signal"] == "BUY":
        emoji = "🟢"

    elif result["signal"] == "SELL":
        emoji = "🔴"

    else:
        emoji = "⚪"


    message = f"""
🟡 <b>GoldPro Signal Bot</b>

{emoji} Signal: <b>{result['signal']}</b>

💰 Entry:
{result['price']}

🎯 TP1:
{result['tp1']}

🎯 TP2:
{result['tp2']}

🛑 SL:
{result['sl']}

📊 Confidence:
{result['confidence']}%

⭐ Quality:
{result['quality']}

📈 Score:
{result['score']}

📌 Reasons:
{', '.join(result['reasons'])}

RSI:
{result['rsi']:.2f}

ADX:
{result['adx']:.2f}

ATR:
{result['atr']:.2f}

⏱ Timeframe:
5 Minutes
"""


    send_signal(message)



print("🟡 GoldPro Signal Bot Started")


# اجرای فوری هنگام شروع
check_market()


# اجرای هر 5 دقیقه
schedule.every(5).minutes.do(check_market)


while True:
    schedule.run_pending()
    time.sleep(10)