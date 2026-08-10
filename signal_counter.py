import json
import os


COUNTER_FILE = "signal_counter.json"


def get_next_signal_id():

    current_id = 0

    if os.path.exists(COUNTER_FILE):

        try:

            with open(
                COUNTER_FILE,
                "r",
                encoding="utf-8"
            ) as file:

                data = json.load(file)

                current_id = int(
                    data.get("last_id", 0)
                )

        except Exception:

            current_id = 0


    next_id = current_id + 1


    with open(
        COUNTER_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            {"last_id": next_id},
            file,
            indent=2
        )


    return f"{next_id:03d}"