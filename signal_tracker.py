import csv
import os
from datetime import datetime


FILE_NAME = "signals_log.csv"


def save_signal(data):

    file_exists = os.path.isfile(FILE_NAME)

    with open(FILE_NAME, "a", newline="", encoding="utf-8") as file:

        writer = csv.writer(file)

        if not file_exists:
            writer.writerow([
                "time",
                "signal",
                "entry",
                "tp1",
                "tp2",
                "sl",
                "confidence",
                "quality"
            ])


        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            data["signal"],
            data["price"],
            data["tp1"],
            data["tp2"],
            data["sl"],
            data["confidence"],
            data["quality"]
        ])