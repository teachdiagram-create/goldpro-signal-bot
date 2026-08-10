import json
import os
import csv


COUNTER_FILE = "signal_counter.json"
RESULT_FILE = "trade_results.csv"
OPEN_FILE = "open_trades.json"


def get_saved_ids_from_results():

    ids = []

    if not os.path.exists(RESULT_FILE):
        return ids

    try:

        with open(
            RESULT_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            reader = csv.DictReader(file)

            for row in reader:

                signal_id = row.get(
                    "signal_id",
                    ""
                )

                if signal_id:

                    try:
                        ids.append(
                            int(signal_id)
                        )
                    except Exception:
                        pass

    except Exception as e:

        print(
            "Signal history read error:",
            e
        )

    return ids


def get_saved_ids_from_open_trades():

    ids = []

    if not os.path.exists(OPEN_FILE):
        return ids

    try:

        with open(
            OPEN_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            trades = json.load(file)

            if isinstance(trades, list):

                for trade in trades:

                    signal_id = trade.get(
                        "signal_id",
                        ""
                    )

                    if signal_id:

                        try:
                            ids.append(
                                int(signal_id)
                            )
                        except Exception:
                            pass

    except Exception as e:

        print(
            "Open trades read error:",
            e
        )

    return ids


def get_counter_id():

    if not os.path.exists(COUNTER_FILE):
        return 0

    try:

        with open(
            COUNTER_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

            return int(
                data.get(
                    "last_id",
                    0
                )
            )

    except Exception as e:

        print(
            "Counter read error:",
            e
        )

        return 0


def get_next_signal_id():

    # -----------------------------------------
    # شماره ذخیره شده در counter
    # -----------------------------------------

    current_id = get_counter_id()

    # -----------------------------------------
    # بررسی شماره‌های ثبت شده در نتایج
    # -----------------------------------------

    result_ids = get_saved_ids_from_results()

    # -----------------------------------------
    # بررسی معاملات باز
    # -----------------------------------------

    open_ids = get_saved_ids_from_open_trades()

    # -----------------------------------------
    # پیدا کردن بزرگترین شماره موجود
    # -----------------------------------------

    all_ids = (
        [current_id]
        + result_ids
        + open_ids
    )

    highest_id = max(
        all_ids,
        default=0
    )

    # -----------------------------------------
    # ساخت شماره بعدی
    # -----------------------------------------

    next_id = highest_id + 1

    # -----------------------------------------
    # ذخیره شماره جدید
    # -----------------------------------------

    try:

        with open(
            COUNTER_FILE,
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
            "Counter save error:",
            e
        )

    signal_id = f"{next_id:03d}"

    print(
        f"Signal Counter: "
        f"new Signal #{signal_id}"
    )

    return signal_id