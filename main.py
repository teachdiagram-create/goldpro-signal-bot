import time
from datetime import datetime

from data_feed import get_gold_data
from indicators import add_indicators
from strategy import generate_signal
from telegram_bot import send_signal
from trade_tracker import add_trade, update_trades


CANDLE_MINUTES = 5
CHECK_DELAY_SECONDS = 5


def format_signal_message(result):

    signal = result.get("signal", "NO SIGNAL")
    signal_id = result.get("signal_id", "000")

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


def format_trade_result(result):

    signal_id = result.get("signal_id", "000")
    signal = result.get("signal", "")
    outcome = result.get("outcome", "")
    price = result.get("price")

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


def check_market():

    print("Checking gold market...")

    try:

        df = get_gold_data()

        if df is None or df.empty:

            print("No data received")

            return

        df = add_indicators(df)

        # =================================================
        # زمان واقعی آخرین کندل دریافتی از Twelve Data
        # =================================================

        signal_candle_time = df.iloc[-1]["time"]

        print(
            f"📌 Current closed candle: "
            f"{signal_candle_time}"
        )

        result = generate_signal(df)

        print(result)

        # =================================================
        # ابتدا معاملات باز را بررسی کن
        # =================================================

        trade_results = update_trades(df)

        for trade_result in trade_results:

            message = format_trade_result(
                trade_result
            )

            send_signal(message)

        # =================================================
        # سپس سیگنال جدید
        # =================================================

        if result.get("signal") in [
            "BUY",
            "SELL"
        ]:

            # ذخیره زمان واقعی کندل سیگنال
            result["signal_candle_time"] = str(
                signal_candle_time
            )

            added = add_trade(
                result,
                signal_candle_time
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


def seconds_until_next_candle():

    now = datetime.now()

    current_seconds = (
        now.minute * 60
        + now.second
        + now.microsecond / 1_000_000
    )

    candle_seconds = CANDLE_MINUTES * 60

    remainder = (
        current_seconds
        % candle_seconds
    )

    wait_seconds = (
        candle_seconds
        - remainder
    )

    return wait_seconds


def main():

    print(
        "🟡 GoldPro Signal Bot Started"
    )

    print(
        "⏱ Waiting for 5-minute candle close..."
    )

    while True:

        try:

            wait_seconds = (
                seconds_until_next_candle()
            )

            print(
                f"Next candle check in "
                f"{wait_seconds:.1f} seconds"
            )

            time.sleep(
                wait_seconds
            )

            time.sleep(
                CHECK_DELAY_SECONDS
            )

            print(
                "🕯 5-minute candle closed"
            )

            check_market()

        except Exception as e:

            print(
                "Main loop error:",
                e
            )

            time.sleep(5)


if __name__ == "__main__":

    main()