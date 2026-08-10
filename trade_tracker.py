import json
import csv
import os
from datetime import datetime, timedelta

from signal_counter import get_next_signal_id


OPEN_FILE = "open_trades.json"
RESULT_FILE = "trade_results.csv"

SL_COOLDOWN_MINUTES = 30
MIN_SIGNAL_DISTANCE = 5.0


# =========================================================
# LOAD OPEN TRADES
# =========================================================

def load_open_trades():

    if not os.path.exists(OPEN_FILE):
        return []

    try:

        with open(
            OPEN_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

            if isinstance(data, list):
                return data

            return []

    except Exception as e:

        print("Open trades load error:", e)

        return []


# =========================================================
# SAVE OPEN TRADES
# =========================================================

def save_open_trades(trades):

    try:

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

    except Exception as e:

        print("Open trades save error:", e)


# =========================================================
# SAVE RESULT
# =========================================================

def save_result(trade, outcome, exit_price):

    file_exists = os.path.exists(RESULT_FILE)

    try:

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

                trade.get(
                    "signal_id",
                    "000"
                ),

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

    except Exception as e:

        print("Result save error:", e)


# =========================================================
# SL COOLDOWN
# =========================================================

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
                remaining.total_seconds()
                / 60
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


# =========================================================
# PRICE DISTANCE
# =========================================================

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


# =========================================================
# ADD NEW TRADE
# =========================================================

def add_trade(result):

    signal = result.get(
        "signal",
        "NO SIGNAL"
    )

    if signal == "NO SIGNAL":
        return False

    trades = load_open_trades()

    new_entry = float(
        result["price"]
    )

    # -----------------------------------------------------
    # فقط یک معامله باز
    # -----------------------------------------------------

    if len(trades) > 0:

        print(
            "Open trade already exists - "
            "new signal ignored"
        )

        return False

    # -----------------------------------------------------
    # Cooldown
    # -----------------------------------------------------

    if is_in_sl_cooldown():

        print(
            "SL cooldown active - "
            "new signal ignored"
        )

        return False

    # -----------------------------------------------------
    # فاصله قیمتی
    # -----------------------------------------------------

    if is_price_too_close(
        new_entry
    ):

        print(
            "Signal price too close - "
            "new signal ignored"
        )

        return False

    # -----------------------------------------------------
    # Signal ID
    # -----------------------------------------------------

    signal_id = get_next_signal_id()

    trade = {

        "id": datetime.now().strftime(
            "%Y%m%d%H%M%S"
        ),

        "signal_id": signal_id,

        "time": datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        ),

        "signal": signal,

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

        "confidence": result.get(
            "confidence",
            0
        ),

        "quality": result.get(
            "quality",
            "UNKNOWN"
        ),

        "tp1_hit": False
    }

    trades.append(trade)

    save_open_trades(
        trades
    )

    # شماره سیگنال برای main.py
    result["signal_id"] = signal_id

    print(
        f"Trade tracker: "
        f"Signal #{signal_id} added"
    )

    print(
        f"Entry={trade['entry']} | "
        f"TP1={trade['tp1']} | "
        f"TP2={trade['tp2']} | "
        f"SL={trade['sl']}"
    )

    return True


# =========================================================
# UPDATE OPEN TRADES
# =========================================================

def update_trades(df):

    trades = load_open_trades()

    if not trades:

        print(
            "Trade tracker: "
            "No open trades"
        )

        return []

    if df is None or df.empty:

        print(
            "Trade tracker: "
            "No market data"
        )

        return []

    print(
        f"Trade tracker: "
        f"{len(trades)} open trade(s)"
    )

    results = []

    remaining = []

    # -----------------------------------------------------
    # برای تشخیص قیمت، همه کندل‌های موجود را بررسی می‌کنیم
    # -----------------------------------------------------

    candles = df.copy()

    # اگر ستون زمان وجود داشته باشد،
    # تلاش می‌کنیم آن را مرتب کنیم.
    try:

        if "time" in candles.columns:

            candles["_tracker_time"] = (
                candles["time"]
                .astype(str)
            )

            candles = candles.sort_values(
                "_tracker_time"
            )

    except Exception:

        pass

    # =====================================================
    # بررسی هر معامله
    # =====================================================

    for trade in trades:

        signal = trade.get(
            "signal"
        )

        signal_id = trade.get(
            "signal_id",
            "000"
        )

        entry = float(
            trade["entry"]
        )

        tp1 = float(
            trade["tp1"]
        )

        tp2 = float(
            trade["tp2"]
        )

        sl = float(
            trade["sl"]
        )

        tp1_hit = bool(
            trade.get(
                "tp1_hit",
                False
            )
        )

        print(
            f"Checking Signal #{signal_id} | "
            f"{signal} | "
            f"Entry={entry} | "
            f"TP1={tp1} | "
            f"TP2={tp2} | "
            f"SL={sl}"
        )

        trade_closed = False
        tp1_reported_now = False

        # -------------------------------------------------
        # کندل‌ها را بررسی می‌کنیم
        # -------------------------------------------------

        for _, candle in candles.iterrows():

            try:

                high = float(
                    candle["high"]
                )

                low = float(
                    candle["low"]
                )

            except Exception:

                continue

            # =================================================
            # BUY
            # =================================================

            if signal == "BUY":

                # -------------------------------------------------
                # SL
                # -------------------------------------------------

                if low <= sl:

                    if tp1_hit:

                        outcome = (
                            "PARTIAL WIN"
                        )

                    else:

                        outcome = "LOSS"

                    print(
                        f"🔴 SL DETECTED | "
                        f"Signal #{signal_id} | "
                        f"Low={low} <= SL={sl}"
                    )

                    save_result(
                        trade,
                        outcome,
                        sl
                    )

                    results.append({

                        "signal_id":
                            signal_id,

                        "signal":
                            signal,

                        "outcome":
                            outcome,

                        "price":
                            sl
                    })

                    trade_closed = True

                    break

                # -------------------------------------------------
                # TP2
                # -------------------------------------------------

                if high >= tp2:

                    print(
                        f"🏆 TP2 DETECTED | "
                        f"Signal #{signal_id} | "
                        f"High={high} >= TP2={tp2}"
                    )

                    save_result(
                        trade,
                        "WIN",
                        tp2
                    )

                    results.append({

                        "signal_id":
                            signal_id,

                        "signal":
                            signal,

                        "outcome":
                            "WIN",

                        "price":
                            tp2
                    })

                    trade_closed = True

                    break

                # -------------------------------------------------
                # TP1
                # -------------------------------------------------

                if high >= tp1:

                    if not tp1_hit:

                        tp1_hit = True

                        trade["tp1_hit"] = True

                        tp1_reported_now = True

                        print(
                            f"🟢 TP1 DETECTED | "
                            f"Signal #{signal_id} | "
                            f"High={high} >= TP1={tp1}"
                        )

                        results.append({

                            "signal_id":
                                signal_id,

                            "signal":
                                signal,

                            "outcome":
                                "TP1 HIT",

                            "price":
                                tp1
                        })

            # =================================================
            # SELL
            # =================================================

            elif signal == "SELL":

                # -------------------------------------------------
                # SL
                # -------------------------------------------------

                if high >= sl:

                    if tp1_hit:

                        outcome = (
                            "PARTIAL WIN"
                        )

                    else:

                        outcome = "LOSS"

                    print(
                        f"🔴 SL DETECTED | "
                        f"Signal #{signal_id} | "
                        f"High={high} >= SL={sl}"
                    )

                    save_result(
                        trade,
                        outcome,
                        sl
                    )

                    results.append({

                        "signal_id":
                            signal_id,

                        "signal":
                            signal,

                        "outcome":
                            outcome,

                        "price":
                            sl
                    })

                    trade_closed = True

                    break

                # -------------------------------------------------
                # TP2
                # -------------------------------------------------

                if low <= tp2:

                    print(
                        f"🏆 TP2 DETECTED | "
                        f"Signal #{signal_id} | "
                        f"Low={low} <= TP2={tp2}"
                    )

                    save_result(
                        trade,
                        "WIN",
                        tp2
                    )

                    results.append({

                        "signal_id":
                            signal_id,

                        "signal":
                            signal,

                        "outcome":
                            "WIN",

                        "price":
                            tp2
                    })

                    trade_closed = True

                    break

                # -------------------------------------------------
                # TP1
                # -------------------------------------------------

                if low <= tp1:

                    if not tp1_hit:

                        tp1_hit = True

                        trade["tp1_hit"] = True

                        tp1_reported_now = True

                        print(
                            f"🟢 TP1 DETECTED | "
                            f"Signal #{signal_id} | "
                            f"Low={low} <= TP1={tp1}"
                        )

                        results.append({

                            "signal_id":
                                signal_id,

                            "signal":
                                signal,

                            "outcome":
                                "TP1 HIT",

                            "price":
                                tp1
                        })

        # -----------------------------------------------------
        # اگر معامله بسته نشده، نگهش می‌داریم
        # -----------------------------------------------------

        if not trade_closed:

            trade["tp1_hit"] = tp1_hit

            remaining.append(
                trade
            )

    # =========================================================
    # ذخیره معاملات باز
    # =========================================================

    save_open_trades(
        remaining
    )

    print(
        f"Trade tracker: "
        f"{len(remaining)} trade(s) remaining"
    )

    return results