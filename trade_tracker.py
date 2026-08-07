import json
import csv
import os
from datetime import datetime


OPEN_FILE = "open_trades.json"
RESULT_FILE = "trade_results.csv"


def load_open_trades():
    if not os.path.exists(OPEN_FILE):
        return []

    try:
        with open(OPEN_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return []


def save_open_trades(trades):
    with open(OPEN_FILE, "w", encoding="utf-8") as file:
        json.dump(trades, file, indent=2, ensure_ascii=False)


def save_result(trade, outcome, exit_price):

    file_exists = os.path.exists(RESULT_FILE)

    with open(
        RESULT_FILE,
        "a",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.writer(file)

        if not file_exists:
            writer.writerow([
                "time",
                "signal",
                "entry",
                "tp1",
                "tp2",
                "sl",
                "exit_price",
                "outcome",
                "confidence",
                "quality"
            ])

        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            trade["signal"],
            trade["entry"],
            trade["tp1"],
            trade["tp2"],
            trade["sl"],
            exit_price,
            outcome,
            trade["confidence"],
            trade["quality"]
        ])


def add_trade(result):

    if result["signal"] == "NO SIGNAL":
        return

    trades = load_open_trades()

    trade = {
        "id": datetime.now().strftime("%Y%m%d%H%M%S"),
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "signal": result["signal"],
        "entry": float(result["price"]),
        "tp1": float(result["tp1"]),
        "tp2": float(result["tp2"]),
        "sl": float(result["sl"]),
        "confidence": result["confidence"],
        "quality": result["quality"],
        "tp1_hit": False
    }

    trades.append(trade)

    save_open_trades(trades)

    print("Trade tracker: trade added")


def update_trades(df):

    trades = load_open_trades()

    if not trades:
        return []


    latest = df.iloc[-1]

    high = float(latest["high"])
    low = float(latest["low"])

    remaining = []
    results = []


    for trade in trades:

        signal = trade["signal"]

        # =========================
        # BUY
        # =========================

        if signal == "BUY":

            # SL
            if low <= trade["sl"]:

                if trade["tp1_hit"]:
                    outcome = "PARTIAL WIN"
                else:
                    outcome = "LOSS"

                save_result(
                    trade,
                    outcome,
                    trade["sl"]
                )

                results.append({
                    "signal": signal,
                    "outcome": outcome,
                    "price": trade["sl"]
                })

                continue


            # TP2
            if high >= trade["tp2"]:

                save_result(
                    trade,
                    "WIN",
                    trade["tp2"]
                )

                results.append({
                    "signal": signal,
                    "outcome": "WIN",
                    "price": trade["tp2"]
                })

                continue


            # TP1
            if high >= trade["tp1"]:

                if not trade["tp1_hit"]:

                    trade["tp1_hit"] = True

                    results.append({
                        "signal": signal,
                        "outcome": "TP1 HIT",
                        "price": trade["tp1"]
                    })


        # =========================
        # SELL
        # =========================

        elif signal == "SELL":

            # SL
            if high >= trade["sl"]:

                if trade["tp1_hit"]:
                    outcome = "PARTIAL WIN"
                else:
                    outcome = "LOSS"

                save_result(
                    trade,
                    outcome,
                    trade["sl"]
                )

                results.append({
                    "signal": signal,
                    "outcome": outcome,
                    "price": trade["sl"]
                })

                continue


            # TP2
            if low <= trade["tp2"]:

                save_result(
                    trade,
                    "WIN",
                    trade["tp2"]
                )

                results.append({
                    "signal": signal,
                    "outcome": "WIN",
                    "price": trade["tp2"]
                })

                continue


            # TP1
            if low <= trade["tp1"]:

                if not trade["tp1_hit"]:

                    trade["tp1_hit"] = True

                    results.append({
                        "signal": signal,
                        "outcome": "TP1 HIT",
                        "price": trade["tp1"]
                    })


        remaining.append(trade)


    save_open_trades(remaining)

    return results