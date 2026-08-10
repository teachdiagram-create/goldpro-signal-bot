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
# Load / Save
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

        print(
            "Open trades read error:",
            e
        )

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


# =========================================================
# Save result
# =========================================================

def save_result(
    trade,
    outcome,
    exit_price,
    candle_time=None
):

    file_exists = os.path.exists(
        RESULT_FILE
    )

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
                "quality",
                "exit_candle"
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

            trade["quality"],

            candle_time or ""
        ])


# =========================================================
# SL Cooldown
# =========================================================

def is_in_sl_cooldown():

    if not os.path.exists(
        RESULT_FILE
    ):

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
            datetime.now()
            - last_time
        )

        cooldown = timedelta(
            minutes=SL_COOLDOWN_MINUTES
        )

        if elapsed < cooldown:

            remaining = (
                cooldown
                - elapsed
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
# Price distance
# =========================================================

def is_price_too_close(
    new_entry
):

    if not os.path.exists(
        RESULT_FILE
    ):

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
            new_entry
            - last_entry
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
# Add trade
# =========================================================

def add_trade(result):

    if result.get("signal") in [
        None,
        "",
        "NO SIGNAL"
    ]:

        return False

    trades = load_open_trades()

    new_signal = result["signal"]

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
    # فاصله قیمت
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

    # -----------------------------------------------------
    # زمان ثبت سیگنال
    # -----------------------------------------------------

    signal_time = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    # -----------------------------------------------------
    # Trade
    # -----------------------------------------------------

    trade = {

        "id": datetime.now().strftime(
            "%Y%m%d%H%M%S"
        ),

        "signal_id": signal_id,

        "time": signal_time,

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

        "tp1_hit": False,

        # زمان آخرین کندل بررسی‌شده
        "last_candle_time": None,

        # ذخیره کندل‌ها
        "candles": []
    }

    # -----------------------------------------------------
    # ذخیره
    # -----------------------------------------------------

    trades.append(trade)

    save_open_trades(
        trades
    )

    # برگرداندن ID به main.py
    result["signal_id"] = signal_id

    print(
        f"Trade tracker: "
        f"Signal #{signal_id} added"
    )

    return True


# =========================================================
# Update trades
# =========================================================

def update_trades(df):

    trades = load_open_trades()

    if not trades:

        print(
            "Trade tracker: No open trades"
        )

        return []

    if df is None or df.empty:

        print(
            "Trade tracker: No candle data"
        )

        return []

    results = []

    remaining = []

    # -----------------------------------------------------
    # بررسی تمام کندل‌ها
    # -----------------------------------------------------

    for trade in trades:

        signal = trade["signal"]

        signal_id = trade.get(
            "signal_id",
            "000"
        )

        entry_time = trade.get(
            "time"
        )

        last_candle_time = trade.get(
            "last_candle_time"
        )

        trade_closed = False

        # -------------------------------------------------
        # بررسی کندل‌ها
        # -------------------------------------------------

        for _, candle in df.iterrows():

            candle_time = str(
                candle["time"]
            )

            # ---------------------------------------------
            # کندل‌های قبل از معامله را رد کن
            # ---------------------------------------------

            if entry_time:

                try:

                    candle_dt = pd_to_datetime(
                        candle_time
                    )

                    entry_dt = pd_to_datetime(
                        entry_time
                    )

                    if candle_dt < entry_dt:

                        continue

                except Exception:

                    pass

            # ---------------------------------------------
            # کندل بررسی‌شده قبلی
            # ---------------------------------------------

            if last_candle_time:

                try:

                    candle_dt = pd_to_datetime(
                        candle_time
                    )

                    last_dt = pd_to_datetime(
                        last_candle_time
                    )

                    if candle_dt <= last_dt:

                        continue

                except Exception:

                    pass

            # ---------------------------------------------
            # High / Low
            # ---------------------------------------------

            high = float(
                candle["high"]
            )

            low = float(
                candle["low"]
            )

            print(
                f"🔎 Signal #{signal_id} | "
                f"Candle: {candle_time} | "
                f"High: {high} | "
                f"Low: {low}"
            )

            # ---------------------------------------------
            # ذخیره کندل
            # ---------------------------------------------

            trade.setdefault(
                "candles",
                []
            )

            trade["candles"].append({

                "time": candle_time,

                "open": float(
                    candle["open"]
                ),

                "high": high,

                "low": low,

                "close": float(
                    candle["close"]
                )
            })

            trade[
                "last_candle_time"
            ] = candle_time

            # =============================================
            # BUY
            # =============================================

            if signal == "BUY":

                # -----------------------------------------
                # SL
                # -----------------------------------------

                if low <= trade["sl"]:

                    if trade["tp1_hit"]:

                        outcome = (
                            "PARTIAL WIN"
                        )

                    else:

                        outcome = "LOSS"

                    save_result(
                        trade,
                        outcome,
                        trade["sl"],
                        candle_time
                    )

                    results.append({

                        "signal_id":
                            signal_id,

                        "signal":
                            signal,

                        "outcome":
                            outcome,

                        "price":
                            trade["sl"]
                    })

                    print(
                        f"🔴 Signal #{signal_id} "
                        f"SL HIT | "
                        f"Low={low} "
                        f"SL={trade['sl']}"
                    )

                    trade_closed = True

                    break

                # -----------------------------------------
                # TP2
                # -----------------------------------------

                if high >= trade["tp2"]:

                    save_result(
                        trade,
                        "WIN",
                        trade["tp2"],
                        candle_time
                    )

                    results.append({

                        "signal_id":
                            signal_id,

                        "signal":
                            signal,

                        "outcome":
                            "WIN",

                        "price":
                            trade["tp2"]
                    })

                    print(
                        f"🏆 Signal #{signal_id} "
                        f"TP2 HIT | "
                        f"High={high} "
                        f"TP2={trade['tp2']}"
                    )

                    trade_closed = True

                    break

                # -----------------------------------------
                # TP1
                # -----------------------------------------

                if high >= trade["tp1"]:

                    if not trade[
                        "tp1_hit"
                    ]:

                        trade[
                            "tp1_hit"
                        ] = True

                        results.append({

                            "signal_id":
                                signal_id,

                            "signal":
                                signal,

                            "outcome":
                                "TP1 HIT",

                            "price":
                                trade["tp1"]
                        })

                        print(
                            f"🟢 Signal #{signal_id} "
                            f"TP1 HIT | "
                            f"High={high} "
                            f"TP1={trade['tp1']}"
                        )

            # =============================================
            # SELL
            # =============================================

            elif signal == "SELL":

                # -----------------------------------------
                # SL
                # -----------------------------------------

                if high >= trade["sl"]:

                    if trade["tp1_hit"]:

                        outcome = (
                            "PARTIAL WIN"
                        )

                    else:

                        outcome = "LOSS"

                    save_result(
                        trade,
                        outcome,
                        trade["sl"],
                        candle_time
                    )

                    results.append({

                        "signal_id":
                            signal_id,

                        "signal":
                            signal,

                        "outcome":
                            outcome,

                        "price":
                            trade["sl"]
                    })

                    print(
                        f"🔴 Signal #{signal_id} "
                        f"SL HIT | "
                        f"High={high} "
                        f"SL={trade['sl']}"
                    )

                    trade_closed = True

                    break

                # -----------------------------------------
                # TP2
                # -----------------------------------------

                if low <= trade["tp2"]:

                    save_result(
                        trade,
                        "WIN",
                        trade["tp2"],
                        candle_time
                    )

                    results.append({

                        "signal_id":
                            signal_id,

                        "signal":
                            signal,

                        "outcome":
                            "WIN",

                        "price":
                            trade["tp2"]
                    })

                    print(
                        f"🏆 Signal #{signal_id} "
                        f"TP2 HIT | "
                        f"Low={low} "
                        f"TP2={trade['tp2']}"
                    )

                    trade_closed = True

                    break

                # -----------------------------------------
                # TP1
                # -----------------------------------------

                if low <= trade["tp1"]:

                    if not trade[
                        "tp1_hit"
                    ]:

                        trade[
                            "tp1_hit"
                        ] = True

                        results.append({

                            "signal_id":
                                signal_id,

                            "signal":
                                signal,

                            "outcome":
                                "TP1 HIT",

                            "price":
                                trade["tp1"]
                        })

                        print(
                            f"🟢 Signal #{signal_id} "
                            f"TP1 HIT | "
                            f"Low={low} "
                            f"TP1={trade['tp1']}"
                        )

        # -------------------------------------------------
        # اگر معامله بسته نشده، نگه دار
        # -------------------------------------------------

        if not trade_closed:

            remaining.append(
                trade
            )

    # -----------------------------------------------------
    # ذخیره معاملات باز
    # -----------------------------------------------------

    save_open_trades(
        remaining
    )

    return results


# =========================================================
# Date helper
# =========================================================

def pd_to_datetime(value):

    from pandas import to_datetime

    return to_datetime(
        value
    )