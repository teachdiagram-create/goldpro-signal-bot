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


def get_next_signal_id(symbol):
    counter_file, result_file, open_file = _files(symbol)

    ids = []

    if os.path.exists(counter_file):
        try:
            with open(counter_file, "r", encoding="utf-8") as file:
                ids.append(int(json.load(file).get("last_id", 0)))
        except Exception:
            pass

    if os.path.exists(result_file):
        try:
            with open(result_file, "r", encoding="utf-8") as file:
                for row in csv.DictReader(file):
                    try:
                        ids.append(int(row.get("signal_id", "0")))
                    except Exception:
                        pass
        except Exception:
            pass

    if os.path.exists(open_file):
        try:
            with open(open_file, "r", encoding="utf-8") as file:
                trades = json.load(file)
                if isinstance(trades, list):
                    for trade in trades:
                        try:
                            ids.append(int(trade.get("signal_id", "0")))
                        except Exception:
                            pass
        except Exception:
            pass

    next_id = max(ids, default=0) + 1

    with open(counter_file, "w", encoding="utf-8") as file:
        json.dump({"last_id": next_id}, file, indent=2)

    signal_id = f"{next_id:03d}"
    print(f"[{symbol}] Signal Counter: new Signal #{signal_id}")
    return signal_id
