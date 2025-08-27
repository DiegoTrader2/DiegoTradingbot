from flask import Flask, request
import requests

app = Flask(__name__)

# 👉 Reemplazar por tu token y chat_id reales
TELEGRAM_BOT_TOKEN = "TELEGRAM_TOKEN"
CHAT_ID = "TELEGRAM_CHAT_ID"

def send_telegram_message(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"  # 👉 Para dar formato si querés
    }
    requests.post(url, json=data)

@app.route("/alert", methods=["POST"])
def alert():
    data = request.get_json(force=True, silent=True) or {}

    signal = str(data.get("signal", "")).lower()
    symbol = data.get("symbol", "N/A")
    price = data.get("price", "N/A")
    interval = data.get("interval", "N/A")
    time = data.get("time", "N/A")

    # Convertimos la señal
    if signal == "buy":
        action = "🟢 COMPRA"
    elif signal == "sell":
        action = "🔴 VENTA"
    else:
        action = "⚠️ Señal desconocida"

    # Mensaje final
    message = f"""
📢 *Alerta TradingView*  
Par: `{symbol}`  
Señal: {action}  
Precio: {price}  
Temporalidad: {interval}  
Hora: {time}
"""

    send_telegram_message(message)
    return "ok", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
