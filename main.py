import time
import schedule

from data_feed import get_gold_data
from indicators import add_indicators
from strategy import generate_signal
from telegram_bot import send_signal
from trade_tracker import add_trade, update_trades


def format_market_message(result):
    signal = result.get("signal", "NO SIGNAL")

    if signal == "BUY":
        title = "🟢 BUY SIGNAL"
    elif signal == "SELL":
        title = "🔴 SELL SIGNAL"
    else:
        title = "⚪ WAITING / NO SIGNAL"

    reasons = ", ".join(result.get("reasons", []))

    return f"""
🟡 <b>GoldPro Signal Bot</b>

{title}

💰 Price:
{result.get("price")}

🎯 TP1:
{result.get("tp1")}

🎯 TP2:
{result.get("tp2")}

🛑 SL:
{result.get("sl")}

📊 Confidence:
{result.get("confidence")}%

⭐ Quality:
{result.get("quality")}

📈 Score:
{result.get("score")}

📌 Reason:
{reasons}

RSI:
{result.get("rsi")}

ADX:
{result.get("adx")}

ATR:
{result.get("atr")}

⏱ Timeframe:
5M
"""


def send_trade_result(result):
    outcome = result["outcome"]
    signal = result["signal"]
    price = result["price"]

    if outcome == "TP1 HIT":
        message = f"""
🟡 <b>GoldPro Trade Update</b>

{signal} SIGNAL

🟢 <b>TP1 HIT</b>

💰 Price:
{price}

📊 Status:
Partial Profit
"""
    
    elif outcome == "WIN":
        message = f"""
🟡 <b>GoldPro Trade Result</b>

{signal} SIGNAL

🟢 <b>TP2 HIT — WIN</b>

💰 Exit:
{price}

🏆 Result:
WIN
"""

    elif outcome == "LOSS":
        message = f"""
🟡 <b>GoldPro Trade Result</b>

{signal} SIGNAL

🔴 <b>SL HIT — LOSS</b>

💰 Exit:
{price}

📉 Result:
LOSS
"""

    elif outcome == "PARTIAL WIN":
        message = f"""
🟡 <b>GoldPro Trade Result</b>

{signal} SIGNAL

🟡 <b>TP1 HIT → SL HIT</b>

💰 Exit:
{price}

📊 Result:
PARTIAL WIN
"""

    else:
        return

    send_signal(message)


def check_market():

    print("Checking gold market...")

    try:

        # --------------------------------
        # دریافت اطلاعات طلا
        # --------------------------------

        df = get_gold_data()

        if df is None or df.empty:
            print("No data received")
            return

        # --------------------------------
        # بررسی معاملات باز
        # --------------------------------

        trade_results = update_trades(df)

        if trade_results:

            for result in trade_results:
                print("Trade result:", result)
                send_trade_result(result)

        # --------------------------------
        # محاسبه اندیکاتورها
        # --------------------------------

        df = add_indicators(df)

        # --------------------------------
        # تولید سیگنال
        # --------------------------------

        result = generate_signal(df)

        print(result)

        # --------------------------------
        # ثبت سیگنال جدید
        # --------------------------------

        if result["signal"] != "NO SIGNAL":

            add_trade(result)

        # --------------------------------
        # ارسال وضعیت به تلگرام
        # --------------------------------

        message = format_market_message(result)

        send_signal(message)

    except Exception as e:

        print("Market check error:", e)


def main():

    print("🟡 GoldPro Signal Bot Started")

    # اجرای فوری
    check_market()

    # اجرای هر 5 دقیقه
    schedule.every(5).minutes.do(check_market)

    while True:

        try:
            schedule.run_pending()
            time.sleep(1)

        except Exception as e:
            print("Scheduler error:", e)
            time.sleep(5)


if __name__ == "__main__":
    main()