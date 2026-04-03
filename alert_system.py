import requests

BOT_TOKEN = "8697340998:AAGkIZoJMgXp0hcfm9TWdvjHrwliOSR0ogg"
CHAT_ID = "669777303"

def send_alert(message):

    url = f"https://api.telegram.org/bot8697340998:AAGkIZoJMgXp0hcfm9TWdvjHrwliOSR0ogg/sendMessage"

    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }

    requests.post(url, data=payload)