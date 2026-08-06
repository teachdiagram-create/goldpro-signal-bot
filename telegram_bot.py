import requests
from config import TELEGRAM_TOKEN, CHAT_ID


def send_signal(message):

    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("Telegram settings missing")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    data = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }

    try:
        response = requests.post(url, data=data)

        if response.status_code == 200:
            print("Telegram message sent")
        else:
            print("Telegram error:", response.text)

    except Exception as e:
        print("Telegram connection error:", e)
