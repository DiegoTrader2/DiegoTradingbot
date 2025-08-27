from flask import Flask, request
import requests

app = Flask(__name__)

# Poner el token y chat_id directo para probar
TELEGRAM_BOT_TOKEN = "TELEGRAM_TOKEN"
CHAT_ID = "TELEGRAM_CHAT_ID"

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message}
    requests.post(url, data=data)

@app.route("/alert", methods=["POST"])
def alert():
    data = request.json

    signal = data.get("signal", "").lower()
    symbol = data.get("symbol", "N/A")
    price = data.get("price", "N/A")
    interval = data.get("interval", "N/A")
    time = data.get("time", "N/A")

    # Convertimos señal
    if signal == "buy":
        action = 📈"COMPRA"
    elif signal == "sell":
        action = 📉"VENTA"
    else:
        action = "⚠️ Señal desconocida"

    message = f"""Par: {symbol}
Señal: {action}
Precio: {price}
Temporalidad: {interval}
Hora: {time}"""

    send_telegram_message(message)
    return "ok", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
