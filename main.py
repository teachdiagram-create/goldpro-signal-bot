import time
import schedule
from datetime import datetime, timezone, timedelta
from signal_tracker import save_signal

from data_feed import get_gold_data
from indicators import add_indicators
from strategy import generate_signal
from telegram_bot import send_signal


def iran_time():
    iran = timezone(timedelta(hours=3, minutes=30))
    return datetime.now(iran).strftime("%Y-%m-%d %H:%M")


def check_market():

    print("Checking gold market...")

    df = get_gold_data()

    if df is None:
        send_signal(
            "🟡 GoldPro Bot\n\n❌ دریافت اطلاعات بازار ناموفق بود"
        )
        return


    df = add_indicators(df)

    result = generate_signal(df)

    print(result)


    signal = result["signal"]


    if signal == "BUY":
        emoji = "🟢"

    elif signal == "SELL":
        emoji = "🔴"

    else:
        emoji = "⚪"



    if signal == "NO SIGNAL":

        message = f"""
🟡 <b>GoldPro Signal Bot</b>

{emoji} وضعیت:
<b>WAITING</b>

💰 Price:
{result['price']}

📊 Confidence:
{result['confidence']}%

📈 Score:
{result['score']}

📌 دلیل:
{', '.join(result['reasons'])}

RSI: {result['rsi']:.2f}
ADX: {result['adx']:.2f}

🕒 Iran Time:
{iran_time()}

⏱ Timeframe:
5M
"""


    else:

        message = f"""
🟡 <b>GoldPro Signal Bot</b>

{emoji} Signal:
<b>{signal}</b>

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

📌 Reason:
{', '.join(result['reasons'])}

RSI:
{result['rsi']:.2f}

ADX:
{result['adx']:.2f}

🕒 Iran Time:
{iran_time()}

⏱ Timeframe:
5M
"""
if result["signal"] != "NO SIGNAL":
    save_signal(result)


    send_signal(message)



print("🟡 GoldPro Signal Bot Started")


check_market()


schedule.every(5).minutes.do(check_market)


while True:
    schedule.run_pending()
    time.sleep(10)