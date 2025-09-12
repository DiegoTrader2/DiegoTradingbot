import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# 🔑 Token y Chat ID (los cargás como variables de entorno en Render)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram_message(message: str) -> bool:
    """Envía mensaje a Telegram y devuelve True/False si fue exitoso"""
    if not TELEGRAM_BOT_TOKEN or not CHAT_ID:
        print("⚠️ Faltan TELEGRAM_TOKEN o TELEGRAM_CHAT_ID en variables de entorno")
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    try:
        r = requests.post(url, json=data, timeout=50)
        ok = r.ok and r.json().get("ok")
        if not ok:
            print("❌ Error al enviar a Telegram:", r.text)
        return ok
    except Exception as e:
        print("⚠️ Excepción al enviar a Telegram:", e)
        return False

@app.route("/")
def home():
    return "OK", 200

@app.route("/alert", methods=["POST"])
def alert():
    data = request.get_json(force=True, silent=True) or {}

    # 📩 Datos que TradingView debe mandar en el JSON de la alerta
    signal = str(data.get("signal", "")).lower()
    symbol = data.get("symbol", "N/A")
    price = data.get("price", "N/A")
    interval = data.get("interval", "N/A")
    time = data.get("time", "N/A")

    # 🎯 Convertimos la señal en texto
    if signal == "buy":
        action = "🟢 COMPRA"
    elif signal == "sell":
        action = "🔴 VENTA"
    else:
        action = "⚠️ Señal desconocida"

    # 📝 Mensaje final
    message = f"""
📊 *Alerta de TradingView*  

📌 Par: {symbol}  
📈 Señal: {action}  
💲 Precio: {price}  
⏱️ Temporalidad: {interval}  
🕒 Hora: {time}  
"""

    ok = send_telegram_message(message)
    return jsonify({"ok": ok}), 200 if ok else 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
