import json
import csv
import os
from datetime import datetime, timedelta

from signal_counter import get_next_signal_id


OPEN_FILE = "open_trades.json"
RESULT_FILE = "trade_results.csv"

SL_COOLDOWN_MINUTES = 30
MIN_SIGNAL_DISTANCE = 5.0


def load_open_trades():

    if not os.path.exists(OPEN_FILE):
        return []

    try:
        with open(
            OPEN_FILE,
            "r",
            encoding="utf-8"
        ) as file:
            return json.load(file)

    except Exception:
        return []


def save_open_trades(trades):

    with open(
        OPEN_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            trades,
            file,
            indent=2,
            ensure_ascii=False
        )


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
                "signal_id",
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
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            trade.get("signal_id", "000"),
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


def is_in_sl_cooldown():

    if not os.path.exists(RESULT_FILE):
        return False

    try:

        with open(
            RESULT_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            rows = list(
                csv.DictReader(file)
            )

        if not rows:
            return False

        last_trade = rows[-1]

        outcome = last_trade.get(
            "outcome",
            ""
        )

        if outcome not in [
            "LOSS",
            "PARTIAL WIN"
        ]:
            return False

        time_text = last_trade.get(
            "time",
            ""
        )

        if not time_text:
            return False

        last_time = datetime.strptime(
            time_text,
            "%Y-%m-%d %H:%M:%S"
        )

        elapsed = (
            datetime.now() - last_time
        )

        cooldown = timedelta(
            minutes=SL_COOLDOWN_MINUTES
        )

        if elapsed < cooldown:

            remaining = (
                cooldown - elapsed
            )

            minutes = int(
                remaining.total_seconds() / 60
            )

            print(
                f"SL cooldown active - "
                f"{minutes} minutes remaining"
            )

            return True

        return False

    except Exception as e:

        print(
            "Cooldown check error:",
            e
        )

        return False


def is_price_too_close(new_entry):

    if not os.path.exists(RESULT_FILE):
        return False

    try:

        with open(
            RESULT_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            rows = list(
                csv.DictReader(file)
            )

        if not rows:
            return False

        last_trade = rows[-1]

        last_entry = float(
            last_trade["entry"]
        )

        distance = abs(
            new_entry - last_entry
        )

        if distance < MIN_SIGNAL_DISTANCE:

            print(
                f"Signal too close - "
                f"distance: {distance:.2f}"
            )

            return True

        return False

    except Exception as e:

        print(
            "Price distance check error:",
            e
        )

        return False


def add_trade(result):

    if result["signal"] == "NO SIGNAL":
        return False

    trades = load_open_trades()

    new_signal = result["signal"]

    new_entry = float(
        result["price"]
    )

    # فقط یک معامله باز
    if len(trades) > 0:

        print(
            "Open trade already exists - "
            "new signal ignored"
        )

        return False

    # Cooldown بعد از SL
    if is_in_sl_cooldown():

        print(
            "SL cooldown active - "
            "new signal ignored"
        )

        return False

    # فاصله قیمتی
    if is_price_too_close(new_entry):

        print(
            "Signal price too close - "
            "new signal ignored"
        )

        return False

    # شماره اختصاصی سیگنال
    signal_id = get_next_signal_id()

    trade = {

        "id": datetime.now().strftime(
            "%Y%m%d%H%M%S"
        ),

        "signal_id": signal_id,

        "time": datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        ),

        "signal": new_signal,

        "entry": new_entry,

        "tp1": float(
            result["tp1"]
        ),

        "tp2": float(
            result["tp2"]
        ),

        "sl": float(
            result["sl"]
        ),

        "confidence": result[
            "confidence"
        ],

        "quality": result[
            "quality"
        ],

        "tp1_hit": False
    }

    trades.append(trade)

    save_open_trades(trades)

    print(
    f"Trade tracker: "
    f"Signal #{signal_id} added"
)

result["signal_id"] = signal_id

return True


def update_trades(df):

    trades = load_open_trades()

    if not trades:
        return []

    latest = df.iloc[-1]

    high = float(
        latest["high"]
    )

    low = float(
        latest["low"]
    )

    remaining = []

    results = []

    for trade in trades:

        signal = trade["signal"]

        signal_id = trade.get(
            "signal_id",
            "000"
        )

        # =========================
        # BUY
        # =========================

        if signal == "BUY":

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
                    "signal_id": signal_id,
                    "signal": signal,
                    "outcome": outcome,
                    "price": trade["sl"]
                })

                continue

            if high >= trade["tp2"]:

                save_result(
                    trade,
                    "WIN",
                    trade["tp2"]
                )

                results.append({
                    "signal_id": signal_id,
                    "signal": signal,
                    "outcome": "WIN",
                    "price": trade["tp2"]
                })

                continue

            if high >= trade["tp1"]:

                if not trade["tp1_hit"]:

                    trade["tp1_hit"] = True

                    results.append({
                        "signal_id": signal_id,
                        "signal": signal,
                        "outcome": "TP1 HIT",
                        "price": trade["tp1"]
                    })

        # =========================
        # SELL
        # =========================

        elif signal == "SELL":

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
                    "signal_id": signal_id,
                    "signal": signal,
                    "outcome": outcome,
                    "price": trade["sl"]
                })

                continue

            if low <= trade["tp2"]:

                save_result(
                    trade,
                    "WIN",
                    trade["tp2"]
                )

                results.append({
                    "signal_id": signal_id,
                    "signal": signal,
                    "outcome": "WIN",
                    "price": trade["tp2"]
                })

                continue

            if low <= trade["tp1"]:

                if not trade["tp1_hit"]:

                    trade["tp1_hit"] = True

                    results.append({
                        "signal_id": signal_id,
                        "signal": signal,
                        "outcome": "TP1 HIT",
                        "price": trade["tp1"]
                    })

        remaining.append(trade)

    save_open_trades(remaining)

    return results