import time
from datetime import datetime

from config import MARKETS, TIMEFRAME, CANDLE_MINUTES, CHECK_DELAY_SECONDS
from data_feed import get_market_data
from mtf_strategy import generate_mtf_signal
from telegram_bot import send_signal
from trade_tracker import add_trade, update_trades


def format_signal_message(symbol, result):
    signal = result.get("signal", "NO SIGNAL")
    signal_id = result.get("signal_id", "000")
    emoji = "🟢" if signal == "BUY" else "🔴" if signal == "SELL" else "⚪"
    title = f"{signal} SIGNAL #{signal_id}" if signal in ["BUY", "SELL"] else "WAITING / NO SIGNAL"
    return f"""🟡 <b>GoldPro — {symbol}</b>\n\n{emoji} <b>{title}</b>\n\n💰 Price:\n{result.get('price')}\n\n🎯 TP1:\n{result.get('tp1')}\n\n🎯 TP2:\n{result.get('tp2')}\n\n🛑 SL:\n{result.get('sl')}\n\n📊 Confidence:\n{result.get('confidence')}%\n\n⭐ Quality:\n{result.get('quality')}\n\n📈 Score:\n{result.get('score')}\n\n📌 Reason:\n{', '.join(result.get('reasons', []))}\n\nRSI:\n{result.get('rsi')}\n\nADX:\n{result.get('adx')}\n\nATR:\n{result.get('atr')}\n\n⏱ Timeframe:\n15M → 5M → 1M""".strip()


def format_trade_result(symbol, result):
    outcome = result.get("outcome", "")
    if outcome == "TP1 HIT":
        emoji, status, desc = "🟢", "TP1 HIT", "Partial Profit"
    elif outcome == "WIN":
        emoji, status, desc = "🏆", "TP2 HIT — WIN", "WIN"
    elif outcome == "PARTIAL WIN":
        emoji, status, desc = "🟡", "SL HIT — PARTIAL WIN", "Partial Profit"
    elif outcome == "LOSS":
        emoji, status, desc = "🔴", "SL HIT — LOSS", "LOSS"
    else:
        emoji, status, desc = "⚪", outcome, outcome
    return f"""🟡 <b>GoldPro Trade Result — {symbol}</b>\n\n📌 Signal #{result.get('signal_id', '000')}\n\n{emoji} <b>{result.get('signal', '')} SIGNAL</b>\n\n<b>{status}</b>\n\n💰 Exit:\n{result.get('price')}\n\n📊 Result:\n{desc}""".strip()


def check_market(symbol):
    print(f"\n========== {symbol} ==========")

    try:

        # ===============================
        # 5M DATA
        # ===============================

        df5 = get_market_data(
            symbol,
            "5min",
            200
        )

        if df5 is None or df5.empty:
            print(f"[{symbol}] No 5M data received")
            return


        # بررسی معاملات باز
        for trade_result in update_trades(symbol, df5):
            send_signal(
                format_trade_result(
                    symbol,
                    trade_result
                )
            )


        # ===============================
        # 15M DATA
        # ===============================

        df15 = get_market_data(
            symbol,
            "15min",
            200
        )

        if df15 is None or df15.empty:
            print(f"[{symbol}] No 15M data received")
            return


        # ===============================
        # 30M DATA
        # ===============================

        df30 = get_market_data(
            symbol,
            "30min",
            200
        )

        if df30 is None or df30.empty:
            print(f"[{symbol}] No 30M data received")
            return


        # ===============================
        # MTF SIGNAL
        # ===============================

        result = generate_mtf_signal(
            df30,
            df15,
            df5
        )


        print(
            f"[{symbol}] MTF signal:",
            result
        )


        # ===============================
        # SEND SIGNAL
        # ===============================

        if result.get("signal") in [
            "BUY",
            "SELL"
        ]:

            signal_candle_time = df5.iloc[-1]["time"]

            result["signal_candle_time"] = str(
                signal_candle_time
            )


            if add_trade(
                symbol,
                result,
                signal_candle_time
            ):

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


def seconds_until_next_candle():
    now = datetime.now()
    current_seconds = now.minute * 60 + now.second + now.microsecond / 1_000_000
    candle_seconds = CANDLE_MINUTES * 60
    remainder = current_seconds % candle_seconds
    return candle_seconds - remainder


def main():
    print("🟡 GoldPro Multi-Timeframe Gold Signal Bot Started")
    print("📊 Markets: XAU/USD")
    print("🎯 Entry: 15M Trend → 5M Pullback → 1M Trigger")
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
