import time
from datetime import datetime

from config import MARKETS, TIMEFRAME, CANDLE_MINUTES, CHECK_DELAY_SECONDS
from data_feed import get_market_data
from indicators import add_indicators
from strategy import generate_signal
from telegram_bot import send_signal
from trade_tracker import add_trade, update_trades


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
{TIMEFRAME}
""".strip()


def format_trade_result(symbol, result):
    signal_id = result.get("signal_id", "000")
    signal = result.get("signal", "")
    outcome = result.get("outcome", "")
    price = result.get("price")

    if outcome == "TP1 HIT":
        emoji, status, description = "🟢", "TP1 HIT", "Partial Profit"
    elif outcome == "WIN":
        emoji, status, description = "🏆", "TP2 HIT — WIN", "WIN"
    elif outcome == "PARTIAL WIN":
        emoji, status, description = "🟡", "SL HIT — PARTIAL WIN", "Partial Profit"
    elif outcome == "LOSS":
        emoji, status, description = "🔴", "SL HIT — LOSS", "LOSS"
    else:
        emoji, status, description = "⚪", outcome, outcome

    return f"""
🟡 <b>GoldPro Trade Result — {symbol}</b>

📌 Signal #{signal_id}

{emoji} <b>{signal} SIGNAL</b>

<b>{status}</b>

💰 Exit:
{price}

📊 Result:
{description}
""".strip()


def check_market(symbol):
    print(f"\n========== {symbol} ==========")
    print(f"[{symbol}] Checking market...")

    try:
        df = get_market_data(symbol)
        if df is None or df.empty:
            print(f"[{symbol}] No data received")
            return

        df = add_indicators(df)
        signal_candle_time = df.iloc[-1]["time"]
        print(f"[{symbol}] Current closed candle: {signal_candle_time}")

        # First close/update existing trade.
        trade_results = update_trades(symbol, df)
        for trade_result in trade_results:
            send_signal(format_trade_result(symbol, trade_result))

        # Then look for a new entry.
        result = generate_signal(df)
        print(f"[{symbol}] {result}")

        if result.get("signal") in ["BUY", "SELL"]:
            result["signal_candle_time"] = str(signal_candle_time)
            added = add_trade(symbol, result, signal_candle_time)
            if added:
                send_signal(format_signal_message(symbol, result))

    except Exception as e:
        print(f"[{symbol}] Market check error:", e)


def seconds_until_next_candle():
    now = datetime.now()
    current_seconds = now.minute * 60 + now.second + now.microsecond / 1_000_000
    candle_seconds = CANDLE_MINUTES * 60
    remainder = current_seconds % candle_seconds
    return candle_seconds - remainder


def main():
    print("🟡 GoldPro Multi-Market Signal Bot Started")
    print("📊 Markets:", ", ".join(MARKETS.keys()))
    print("⏱ Waiting for 5-minute candle close...")

    while True:
        try:
            wait_seconds = seconds_until_next_candle()
            print(f"Next candle check in {wait_seconds:.1f} seconds")
            time.sleep(wait_seconds)
            time.sleep(CHECK_DELAY_SECONDS)
            print("🕯 5-minute candle closed")

            for symbol in MARKETS:
                check_market(symbol)

        except Exception as e:
            print("Main loop error:", e)
            time.sleep(5)


if __name__ == "__main__":
    main()
