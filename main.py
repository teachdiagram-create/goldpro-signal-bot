import time
from datetime import datetime

from data_feed import get_gold_data
from indicators import add_indicators
from strategy import generate_signal
from telegram_bot import send_signal
from trade_tracker import add_trade, update_trades


# =========================================================
# تنظیمات
# =========================================================

CANDLE_MINUTES = 5
CHECK_DELAY_SECONDS = 5


# =========================================================
# پیام سیگنال
# =========================================================

def format_signal_message(result):

    signal = result.get(
        "signal",
        "NO SIGNAL"
    )

    signal_id = result.get(
        "signal_id",
        "000"
    )

    if signal == "BUY":

        emoji = "🟢"
        title = f"BUY SIGNAL #{signal_id}"

    elif signal == "SELL":

        emoji = "🔴"
        title = f"SELL SIGNAL #{signal_id}"

    else:

        emoji = "⚪"
        title = "WAITING / NO SIGNAL"

    message = f"""
🟡 <b>GoldPro Signal #{signal_id}</b>

{emoji} <b>{title}</b>

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
{", ".join(result.get("reasons", []))}

RSI:
{result.get("rsi")}

ADX:
{result.get("adx")}

ATR:
{result.get("atr")}

⏱ Timeframe:
5M
"""

    return message.strip()


# =========================================================
# پیام نتیجه معامله
# =========================================================

def format_trade_result(result):

    signal_id = result.get(
        "signal_id",
        "000"
    )

    signal = result.get(
        "signal",
        ""
    )

    outcome = result.get(
        "outcome",
        ""
    )

    price = result.get(
        "price"
    )

    if outcome == "TP1 HIT":

        emoji = "🟢"
        status = "TP1 HIT"
        description = "Partial Profit"

    elif outcome == "WIN":

        emoji = "🏆"
        status = "TP2 HIT — WIN"
        description = "WIN"

    elif outcome == "PARTIAL WIN":

        emoji = "🟡"
        status = "SL HIT — PARTIAL WIN"
        description = "Partial Profit"

    elif outcome == "LOSS":

        emoji = "🔴"
        status = "SL HIT — LOSS"
        description = "LOSS"

    else:

        emoji = "⚪"
        status = outcome
        description = outcome

    message = f"""
🟡 <b>GoldPro Trade Result</b>

📌 Signal #{signal_id}

{emoji} <b>{signal} SIGNAL</b>

<b>{status}</b>

💰 Exit:
{price}

📊 Result:
{description}
"""

    return message.strip()


# =========================================================
# بررسی بازار
# =========================================================

def check_market():

    print(
        "Checking gold market..."
    )

    try:

        # -------------------------------------------------
        # دریافت داده
        # -------------------------------------------------

        df = get_gold_data()

        if df is None or df.empty:

            print(
                "No data received"
            )

            return

        # -------------------------------------------------
        # اندیکاتورها
        # -------------------------------------------------

        df = add_indicators(df)

        # -------------------------------------------------
        # تولید سیگنال
        # -------------------------------------------------

        result = generate_signal(df)

        print(result)

        # -------------------------------------------------
        # بررسی معاملات باز
        # -------------------------------------------------

        trade_results = update_trades(df)

        for trade_result in trade_results:

            message = format_trade_result(
                trade_result
            )

            send_signal(message)

        # -------------------------------------------------
        # ثبت سیگنال جدید
        # -------------------------------------------------

        if result.get("signal") in [
            "BUY",
            "SELL"
        ]:

            added = add_trade(
                result
            )

            if added:

                message = format_signal_message(
                    result
                )

                send_signal(message)

    except Exception as e:

        print(
            "Market check error:",
            e
        )


# =========================================================
# محاسبه زمان تا کندل 5 دقیقه‌ای بعدی
# =========================================================

def seconds_until_next_candle():

    now = datetime.now()

    current_seconds = (
        now.minute * 60
        + now.second
        + now.microsecond / 1_000_000
    )

    candle_seconds = (
        CANDLE_MINUTES * 60
    )

    remainder = (
        current_seconds
        % candle_seconds
    )

    wait_seconds = (
        candle_seconds
        - remainder
    )

    return wait_seconds


# =========================================================
# اجرای اصلی
# =========================================================

def main():

    print(
        "🟡 GoldPro Signal Bot Started"
    )

    print(
        "⏱ Waiting for 5-minute candle close..."
    )

    while True:

        try:

            # -------------------------------------------------
            # محاسبه زمان بسته‌شدن کندل بعدی
            # -------------------------------------------------

            wait_seconds = (
                seconds_until_next_candle()
            )

            print(
                f"Next candle check in "
                f"{wait_seconds:.1f} seconds"
            )

            # -------------------------------------------------
            # صبر تا بسته‌شدن کندل
            # -------------------------------------------------

            time.sleep(
                wait_seconds
            )

            # -------------------------------------------------
            # چند ثانیه تأخیر برای اطمینان از بسته‌شدن کندل
            # -------------------------------------------------

            time.sleep(
                CHECK_DELAY_SECONDS
            )

            print(
                "🕯 5-minute candle closed"
            )

            # -------------------------------------------------
            # اجرای تحلیل
            # -------------------------------------------------

            check_market()

        except Exception as e:

            print(
                "Main loop error:",
                e
            )

            # جلوگیری از توقف کامل Worker
            time.sleep(5)


# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    main()