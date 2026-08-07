import time
import schedule
from datetime import datetime, timezone, timedelta

from data_feed import get_gold_data
from indicators import add_indicators
from strategy import generate_signal
from telegram_bot import send_signal
from signal_tracker import save_signal


def iran_time():
    iran = timezone(timedelta(hours=3, minutes=30))
    return datetime.now(iran).strftime("%Y-%m-%d %H:%M")


def check_market():

    print("Checking gold market...")

    df = get_gold_data()

    if df is None:
        print("No data received")

        send_signal(
            "🟡 <b>GoldPro Signal Bot</b>\n\n"
            "❌ دریافت اطلاعات بازار ناموفق بود"
        )

        return

    try:
        df = add_indicators(df)

        result = generate_signal(df)

        print(result)

    except Exception as e:
        print("Analysis error:", e)

        send_signal(
            "🟡 <b>GoldPro Signal Bot</b>\n\n"
            f"❌ خطا در تحلیل بازار:\n{e}"
        )

        return


    signal = result["signal"]


    # --------------------------------
    # BUY / SELL
    # --------------------------------

    if signal == "BUY":

        message = f"""
🟡 <b>GoldPro Signal Bot</b>

🟢 <b>BUY SIGNAL</b>

💰 Entry:
<b>{result['price']:.2f}</b>

🎯 TP1:
<b>{result['tp1']:.2f}</b>

🎯 TP2:
<b>{result['tp2']:.2f}</b>

🛑 SL:
<b>{result['sl']:.2f}</b>

📊 Confidence:
<b>{result['confidence']}%</b>

⭐ Quality:
<b>{result['quality']}</b>

📈 Score:
<b>{result['score']}</b>

📌 Reason:
{', '.join(result['reasons'])}

RSI:
{result['rsi']:.2f}

ADX:
{result['adx']:.2f}

ATR:
{result['atr']:.2f}

🕒 Iran Time:
{iran_time()}

⏱ Timeframe:
<b>5M</b>
"""


    elif signal == "SELL":

        message = f"""
🟡 <b>GoldPro Signal Bot</b>

🔴 <b>SELL SIGNAL</b>

💰 Entry:
<b>{result['price']:.2f}</b>

🎯 TP1:
<b>{result['tp1']:.2f}</b>

🎯 TP2:
<b>{result['tp2']:.2f}</b>

🛑 SL:
<b>{result['sl']:.2f}</b>

📊 Confidence:
<b>{result['confidence']}%</b>

⭐ Quality:
<b>{result['quality']}</b>

📈 Score:
<b>{result['score']}</b>

📌 Reason:
{', '.join(result['reasons'])}

RSI:
{result['rsi']:.2f}

ADX:
{result['adx']:.2f}

ATR:
{result['atr']:.2f}

🕒 Iran Time:
{iran_time()}

⏱ Timeframe:
<b>5M</b>
"""


    # --------------------------------
    # NO SIGNAL
    # --------------------------------

    else:

        message = f"""
🟡 <b>GoldPro Signal Bot</b>

⚪ <b>WAITING / NO SIGNAL</b>

💰 Price:
<b>{result['price']:.2f}</b>

📊 Confidence:
<b>{result['confidence']}%</b>

⭐ Quality:
<b>{result['quality']}</b>

📈 Score:
<b>{result['score']}</b>

📌 Reason:
{', '.join(result['reasons'])}

RSI:
{result['rsi']:.2f}

ADX:
{result['adx']:.2f}

ATR:
{result['atr']:.2f}

🕒 Iran Time:
{iran_time()}

⏱ Timeframe:
<b>5M</b>
"""


    # --------------------------------
    # ذخیره فقط BUY / SELL
    # --------------------------------

    if signal != "NO SIGNAL":

        try:
            save_signal(result)
            print("Signal saved successfully")

        except Exception as e:
            print("Tracker error:", e)


    # --------------------------------
    # ارسال پیام تلگرام
    # --------------------------------

    send_signal(message)


# --------------------------------
# شروع ربات
# --------------------------------

print("🟡 GoldPro Signal Bot Started")


# اجرای فوری
check_market()


# اجرای هر 5 دقیقه
schedule.every(5).minutes.do(check_market)


while True:

    schedule.run_pending()

    time.sleep(10)