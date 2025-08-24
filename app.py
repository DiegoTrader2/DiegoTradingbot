from flask import Flask, request
import requests
import os

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

@app.route('/alert', methods=['POST'])
def alert():
    data = request.json
    print("📩 Alerta recibida:", data)  # Debug para ver qué llega

    if not data:
        return "No JSON recibido", 400

    message = data.get("message", "⚠️ Alerta sin mensaje")
    print("➡️ Enviando a Telegram:", message)  # Debug

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}

    r = requests.post(url, json=payload)
    print("✅ Respuesta Telegram:", r.status_code, r.text)  # Debug

    return "ok", 200
