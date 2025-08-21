
import os, json, requests
from flask import Flask, request, jsonify

app = Flask(__name__)

TOKEN = os.environ.get("TELEGRAM_TOKEN")  # lo ponemos en Render
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")  # lo ponemos en Render

def send_telegram(text: str):
    if not TOKEN or not CHAT_ID:
        return False, "Faltan TELEGRAM_TOKEN o TELEGRAM_CHAT_ID"
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",  # más seguro que HTML
        "disable_web_page_preview": True
    }
    r = requests.post(url, json=payload, timeout=10)
    ok = r.ok and r.json().get("ok")
    return ok, r.text

@app.route("/")
def home():
    return "OK", 200

# Endpoint para TradingView
@app.route("/alert", methods=["POST"])
def alert():
    data = request.get_json(silent=True) or {}

    mensaje = data.get("message", "")
    precio = data.get("price", "")
    symbol = data.get("symbol", "")

    # Hora UTC y la ajustamos a Argentina (UTC-3)
    from datetime import datetime, timedelta
    hora_utc = datetime.utcnow()
    hora_arg = hora_utc - timedelta(hours=3)
    hora = hora_arg.strftime("%A %d-%m-%Y %H:%M:%S")  # incluye día de la semana

    texto = (
        f"🚨 *Alerta de TradingView*\n\n"
        f"📊 Par: {symbol}\n"
        f"💬 Mensaje: {mensaje}\n"
        f"💰 Precio: {precio}\n"
        f"⏰ Hora (ARG): {hora}"
    )

    ok = send_telegram(texto)
    return jsonify({"ok": ok}), 200 if ok else 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Render te da PORT
    app.run(host="0.0.0.0", port=port)
