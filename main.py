import time

from data_feed import get_gold_data
from indicators import add_indicators
from strategy import generate_signal
from telegram_bot import send_signal
from trade_tracker import add_trade, update_trades


CHECK_INTERVAL = 300


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


def check_market():

    print("Checking gold market...")

    try:

        df = get_gold_data()

        if df is None or df.empty:

            print("No data received")

            return

        df = add_indicators(df)

        result = generate_signal(df)

        print(result)

        # =========================
        # Update existing trades
        # =========================

        trade_results = update_trades(df)

        for trade_result in trade_results:

            message = format_trade_result(
                trade_result
            )

            send_signal(message)

        # =========================
        # New signal
        # =========================

        if result.get("signal") in [
            "BUY",
            "SELL"
        ]:

            added = add_trade(result)

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


def main():

    print(
        "🟡 GoldPro Signal Bot Started"
    )

    while True:

        check_market()

        time.sleep(
            CHECK_INTERVAL
        )


if __name__ == "__main__":

    main()