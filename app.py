from flask import Flask, request
import requests
import os

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message}
    requests.post(url, data=data)

@app.route("/alert", methods=["POST"])
def alert():
    data = request.json

    signal = data.get("signal", "Alerta")
    symbol = data.get("symbol", "N/A")
    price = data.get("price", "N/A")
    interval = data.get("interval", "N/A")
    time = data.get("time", "N/A")

    # Convertimos señal a texto claro
    if signal.lower() == "buy":
        action = "📈 Posible COMPRA"
    elif signal.lower() == "sell":
        action = "📉 Posible VENTA"
    else:
        action = "⚠️ Señal detectada"

    message = f"""{action}
Par: {symbol}
Precio: {price}
Temporalidad: {interval}
Hora: {time}"""

    send_telegram_message(message)
    return "ok", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
