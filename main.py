import time
from datetime import datetime

from config import MARKETS, TIMEFRAME, CANDLE_MINUTES, CHECK_DELAY_SECONDS
from data_feed import get_market_data
from mtf_strategy import generate_mtf_signal
from telegram_bot import send_signal
from trade_tracker import add_trade, update_trades


# =========================================================
# TELEGRAM SIGNAL MESSAGE
# =========================================================

def format_signal_message(symbol, result):

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

    return f"""
🟡 <b>GoldPro — {symbol}</b>

{emoji} <b>{title}</b>

💰 Price:
{result.get('price')}

🎯 TP1:
{result.get('tp1')}

🎯 TP2:
{result.get('tp2')}

🛑 SL:
{result.get('sl')}

📊 Confidence:
{result.get('confidence')}%

⭐ Quality:
{result.get('quality')}

📈 Score:
{result.get('score')}

📌 Reason:
{', '.join(result.get('reasons', []))}

RSI:
{result.get('rsi')}

ADX:
{result.get('adx')}

ATR:
{result.get('atr')}

⏱ Timeframe:
30M → 15M → 5M
""".strip()


# =========================================================
# TRADE RESULT MESSAGE
# =========================================================

def format_trade_result(symbol, result):

    outcome = result.get("outcome", "")

    if outcome == "TP1 HIT":
        emoji = "🟢"
        status = "TP1 HIT"
        desc = "Partial Profit"

    elif outcome == "WIN":
        emoji = "🏆"
        status = "TP2 HIT — WIN"
        desc = "WIN"

    elif outcome == "PARTIAL WIN":
        emoji = "🟡"
        status = "SL HIT — PARTIAL WIN"
        desc = "Partial Profit"

    elif outcome == "LOSS":
        emoji = "🔴"
        status = "SL HIT — LOSS"
        desc = "LOSS"

    else:
        emoji = "⚪"
        status = outcome
        desc = outcome

    return f"""
🟡 <b>GoldPro Trade Result — {symbol}</b>

📌 Signal #{result.get('signal_id', '000')}

{emoji} <b>{result.get('signal', '')} SIGNAL</b>

<b>{status}</b>

💰 Exit:
{result.get('price')}

📊 Result:
{desc}
""".strip()


# =========================================================
# CHECK GOLD MARKET
# =========================================================

def check_market(symbol):

    print(f"\n========== {symbol} ==========")

    try:

        # =================================================
        # 5 MINUTE DATA
        # =================================================

        df5 = get_market_data(
            symbol,
            "5min",
            200
        )

        if df5 is None or df5.empty:

            print(
                f"[{symbol}] No 5M data received"
            )

            return


        # =================================================
        # UPDATE EXISTING TRADES
        # =================================================

        for trade_result in update_trades(
            symbol,
            df5
        ):

            send_signal(
                format_trade_result(
                    symbol,
                    trade_result
                )
            )


        # =================================================
        # 15 MINUTE DATA
        # =================================================

        df15 = get_market_data(
            symbol,
            "15min",
            200
        )

        if df15 is None or df15.empty:

            print(
                f"[{symbol}] No 15M data received"
            )

            return


        # =================================================
        # 30 MINUTE DATA
        # =================================================

        df30 = get_market_data(
            symbol,
            "30min",
            200
        )

        if df30 is None or df30.empty:

            print(
                f"[{symbol}] No 30M data received"
            )

            return


        # =================================================
        # MULTI-TIMEFRAME ANALYSIS
        #
        # 30M → MAIN TREND
        # 15M → CONFIRMATION
        # 5M  → ENTRY
        # =================================================

        result = generate_mtf_signal(
            df30,
            df15,
            df5
        )

        print(
            f"[{symbol}] MTF signal:",
            result
        )


        # =================================================
        # NEW SIGNAL
        # =================================================

        if result.get("signal") in [
            "BUY",
            "SELL"
        ]:

            signal_candle_time = (
                df5.iloc[-1]["time"]
            )

            result[
                "signal_candle_time"
            ] = str(
                signal_candle_time
            )


            added = add_trade(
                symbol,
                result,
                signal_candle_time
            )


            if added:

                send_signal(
                    format_signal_message(
                        symbol,
                        result
                    )
                )


    except Exception as e:

        print(
            f"[{symbol}] Market check error:",
            e
        )


# =========================================================
# WAIT FOR NEXT 5M CANDLE
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

    return (
        candle_seconds
        - remainder
    )


# =========================================================
# MAIN LOOP
# =========================================================

def main():

    print(
        "🟡 GoldPro Multi-Timeframe Gold Signal Bot Started"
    )

    print(
        "📊 Markets: XAU/USD"
    )

    print(
        "🎯 Entry: 30M Trend → 15M Confirmation → 5M Entry"
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


            # فقط بازار طلا
            for symbol in MARKETS:

                check_market(
                    symbol
                )


        except Exception as e:

            print(
                "Main loop error:",
                e
            )

            time.sleep(5)


# =========================================================
# START BOT
# =========================================================

if __name__ == "__main__":

    main()