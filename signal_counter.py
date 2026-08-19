import csv
import json
import os


def _safe_name(symbol):
    return symbol.replace("/", "_").replace("\\", "_")


def _files(symbol):
    name = _safe_name(symbol)
    base = os.path.join("data", name)
    os.makedirs(base, exist_ok=True)

    return (
        os.path.join(base, "signal_counter.json"),
        os.path.join(base, "trade_results.csv"),
        os.path.join(base, "open_trades.json"),
    )


def _read_counter(counter_file):
    if not os.path.exists(counter_file):
        return 0

    try:
        with open(counter_file, "r", encoding="utf-8") as file:
            data = json.load(file)

        return int(data.get("last_id", 0))

    except Exception as e:
        print("Signal counter read error:", e)
        return 0


def _read_result_ids(result_file):
    ids = []

    if not os.path.exists(result_file):
        return ids

    try:
        with open(result_file, "r", encoding="utf-8") as file:
            for row in csv.DictReader(file):

                try:
                    signal_id = int(row.get("signal_id", "0"))
                    if signal_id > 0:
                        ids.append(signal_id)
                except Exception:
                    continue

    except Exception as e:
        print("Trade results counter read error:", e)

    return ids


def _read_open_trade_ids(open_file):
    ids = []

    if not os.path.exists(open_file):
        return ids

    try:
        with open(open_file, "r", encoding="utf-8") as file:
            trades = json.load(file)

        if not isinstance(trades, list):
            return ids

        for trade in trades:

            try:
                signal_id = int(trade.get("signal_id", "0"))

                if signal_id > 0:
                    ids.append(signal_id)

            except Exception:
                continue

    except Exception as e:
        print("Open trades counter read error:", e)

    return ids


def get_next_signal_id(symbol):

    counter_file, result_file, open_file = _files(symbol)

    # -------------------------------------------------
    # Collect every known signal ID
    # -------------------------------------------------

    ids = []

    # Counter file
    ids.append(
        _read_counter(counter_file)
    )

    # Closed trades
    ids.extend(
        _read_result_ids(result_file)
    )

    # Open trades
    ids.extend(
        _read_open_trade_ids(open_file)
    )

    # -------------------------------------------------
    # Find highest existing ID
    # -------------------------------------------------

    last_id = max(ids, default=0)

    # -------------------------------------------------
    # Generate next ID
    # -------------------------------------------------

    next_id = last_id + 1

    # -------------------------------------------------
    # Save counter immediately
    # -------------------------------------------------

    try:

        with open(
            counter_file,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                {
                    "last_id": next_id
                },
                file,
                indent=2
            )

    except Exception as e:

        print(
            "Signal counter save error:",
            e
        )

    signal_id = f"{next_id:03d}"

    print(
        f"[{symbol}] Signal Counter: "
        f"new Signal #{signal_id}"
    )

    return signal_id