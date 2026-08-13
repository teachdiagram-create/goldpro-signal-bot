import csv
import json
import os
from datetime import datetime, timedelta

from signal_counter import get_next_signal_id

SL_COOLDOWN_MINUTES = 30
MIN_SIGNAL_DISTANCE = 5.0


def _safe_name(symbol):
    return symbol.replace("/", "_").replace("\\", "_")


def _files(symbol):
    base = os.path.join("data", _safe_name(symbol))
    os.makedirs(base, exist_ok=True)
    return (
        os.path.join(base, "open_trades.json"),
        os.path.join(base, "trade_results.csv"),
    )


def load_open_trades(symbol):
    open_file, _ = _files(symbol)
    if not os.path.exists(open_file):
        return []
    try:
        with open(open_file, "r", encoding="utf-8") as file:
            data = json.load(file)
            return data if isinstance(data, list) else []
    except Exception as e:
        print(f"[{symbol}] Open trades read error:", e)
        return []


def save_open_trades(symbol, trades):
    open_file, _ = _files(symbol)
    with open(open_file, "w", encoding="utf-8") as file:
        json.dump(trades, file, indent=2, ensure_ascii=False)


def save_result(symbol, trade, outcome, exit_price, candle_time=None):
    _, result_file = _files(symbol)
    file_exists = os.path.exists(result_file)

    with open(result_file, "a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow([
                "time", "signal_id", "signal", "entry", "tp1", "tp2",
                "sl", "exit_price", "outcome", "confidence", "quality",
                "exit_candle"
            ])

        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            trade.get("signal_id", "000"),
            trade["signal"], trade["entry"], trade["tp1"], trade["tp2"],
            trade["sl"], exit_price, outcome, trade["confidence"],
            trade["quality"], candle_time or ""
        ])


def is_in_sl_cooldown(symbol):
    _, result_file = _files(symbol)
    if not os.path.exists(result_file):
        return False

    try:
        with open(result_file, "r", encoding="utf-8") as file:
            rows = list(csv.DictReader(file))
        if not rows:
            return False

        last = rows[-1]
        if last.get("outcome") not in ["LOSS", "PARTIAL WIN"]:
            return False

        text = last.get("time", "")
        if not text:
            return False

        elapsed = datetime.now() - datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
        cooldown = timedelta(minutes=SL_COOLDOWN_MINUTES)
        if elapsed < cooldown:
            remaining = int((cooldown - elapsed).total_seconds() / 60)
            print(f"[{symbol}] SL cooldown active - {remaining} minutes remaining")
            return True
        return False
    except Exception as e:
        print(f"[{symbol}] Cooldown check error:", e)
        return False


def is_price_too_close(symbol, new_entry):
    _, result_file = _files(symbol)
    if not os.path.exists(result_file):
        return False

    try:
        with open(result_file, "r", encoding="utf-8") as file:
            rows = list(csv.DictReader(file))
        if not rows:
            return False

        distance = abs(new_entry - float(rows[-1]["entry"]))
        if distance < MIN_SIGNAL_DISTANCE:
            print(f"[{symbol}] Signal too close - distance: {distance:.2f}")
            return True
        return False
    except Exception as e:
        print(f"[{symbol}] Price distance check error:", e)
        return False


def add_trade(symbol, result, signal_candle_time):
    if result.get("signal") in [None, "", "NO SIGNAL"]:
        return False

    trades = load_open_trades(symbol)
    new_entry = float(result["price"])

    if trades:
        print(f"[{symbol}] Open trade already exists - new signal ignored")
        return False

    if is_in_sl_cooldown(symbol):
        print(f"[{symbol}] SL cooldown active - new signal ignored")
        return False

    if is_price_too_close(symbol, new_entry):
        print(f"[{symbol}] Signal price too close - new signal ignored")
        return False

    signal_id = get_next_signal_id(symbol)
    signal_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    trade = {
        "id": datetime.now().strftime("%Y%m%d%H%M%S"),
        "signal_id": signal_id,
        "time": signal_time,
        "signal_candle_time": str(signal_candle_time),
        "signal": result["signal"],
        "entry": new_entry,
        "tp1": float(result["tp1"]),
        "tp2": float(result["tp2"]),
        "sl": float(result["sl"]),
        "confidence": result["confidence"],
        "quality": result["quality"],
        "tp1_hit": False,
        "last_candle_time": str(signal_candle_time),
        "candles": []
    }

    trades.append(trade)
    save_open_trades(symbol, trades)
    result["signal_id"] = signal_id

    print(f"[{symbol}] Trade tracker: Signal #{signal_id} added")
    print(f"[{symbol}] Signal candle: {signal_candle_time}")
    return True


def pd_to_datetime(value):
    from pandas import to_datetime
    return to_datetime(value)


def update_trades(symbol, df):
    trades = load_open_trades(symbol)
    if not trades:
        print(f"[{symbol}] Trade tracker: No open trades")
        return []
    if df is None or df.empty:
        print(f"[{symbol}] Trade tracker: No candle data")
        return []

    results = []
    remaining = []

    for trade in trades:
        signal = trade["signal"]
        signal_id = trade.get("signal_id", "000")
        signal_candle_time = trade.get("signal_candle_time")
        last_candle_time = trade.get("last_candle_time")
        trade_closed = False

        for _, candle in df.iterrows():
            candle_time = str(candle["time"])
            try:
                candle_dt = pd_to_datetime(candle_time)
            except Exception:
                continue

            if signal_candle_time:
                try:
                    if candle_dt <= pd_to_datetime(signal_candle_time):
                        continue
                except Exception:
                    pass

            if last_candle_time:
                try:
                    if candle_dt <= pd_to_datetime(last_candle_time):
                        continue
                except Exception:
                    pass

            high = float(candle["high"])
            low = float(candle["low"])

            print(f"🔎 [{symbol}] Signal #{signal_id} | Candle: {candle_time} | High: {high} | Low: {low}")

            trade.setdefault("candles", []).append({
                "time": candle_time,
                "open": float(candle["open"]),
                "high": high,
                "low": low,
                "close": float(candle["close"])
            })
            trade["last_candle_time"] = candle_time

            if signal == "BUY":
                if low <= float(trade["sl"]):
                    outcome = "PARTIAL WIN" if trade["tp1_hit"] else "LOSS"
                    save_result(symbol, trade, outcome, trade["sl"], candle_time)
                    results.append({"signal_id": signal_id, "signal": signal, "outcome": outcome, "price": trade["sl"]})
                    print(f"🔴 [{symbol}] Signal #{signal_id} SL HIT | Low={low} SL={trade['sl']}")
                    trade_closed = True
                    break

                if high >= float(trade["tp2"]):
                    save_result(symbol, trade, "WIN", trade["tp2"], candle_time)
                    results.append({"signal_id": signal_id, "signal": signal, "outcome": "WIN", "price": trade["tp2"]})
                    print(f"🏆 [{symbol}] Signal #{signal_id} TP2 HIT | High={high} TP2={trade['tp2']}")
                    trade_closed = True
                    break

                if high >= float(trade["tp1"]) and not trade["tp1_hit"]:
                    trade["tp1_hit"] = True
                    results.append({"signal_id": signal_id, "signal": signal, "outcome": "TP1 HIT", "price": trade["tp1"]})
                    print(f"🟢 [{symbol}] Signal #{signal_id} TP1 HIT | High={high} TP1={trade['tp1']}")

            elif signal == "SELL":
                if high >= float(trade["sl"]):
                    outcome = "PARTIAL WIN" if trade["tp1_hit"] else "LOSS"
                    save_result(symbol, trade, outcome, trade["sl"], candle_time)
                    results.append({"signal_id": signal_id, "signal": signal, "outcome": outcome, "price": trade["sl"]})
                    print(f"🔴 [{symbol}] Signal #{signal_id} SL HIT | High={high} SL={trade['sl']}")
                    trade_closed = True
                    break

                if low <= float(trade["tp2"]):
                    save_result(symbol, trade, "WIN", trade["tp2"], candle_time)
                    results.append({"signal_id": signal_id, "signal": signal, "outcome": "WIN", "price": trade["tp2"]})
                    print(f"🏆 [{symbol}] Signal #{signal_id} TP2 HIT | Low={low} TP2={trade['tp2']}")
                    trade_closed = True
                    break

                if low <= float(trade["tp1"]) and not trade["tp1_hit"]:
                    trade["tp1_hit"] = True
                    results.append({"signal_id": signal_id, "signal": signal, "outcome": "TP1 HIT", "price": trade["tp1"]})
                    print(f"🟢 [{symbol}] Signal #{signal_id} TP1 HIT | Low={low} TP1={trade['tp1']}")

        if not trade_closed:
            remaining.append(trade)

    save_open_trades(symbol, remaining)
    return results
