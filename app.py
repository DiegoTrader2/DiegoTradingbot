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

    # Extraemos los datos enviados desde TradingView
    par = data.get("par", "Desconocido")
    precio = data.get("precio", "N/A")
    temporalidad = data.get("temporalidad", "N/A")
    hora = data.get("hora", "N/A")
    rsi = float(data.get("rsi", 0))

    # Armamos el mensaje según el valor del RSI
    if rsi < 30:
        mensaje_alerta = "🟢 COMPRA"
    elif rsi > 70:
        mensaje_alerta = "🔴 VENTA"
    else:
        mensaje_alerta = f"ℹ️ RSI en rango ({rsi})"

    # Construcción final del mensaje
    message = (
        f"🚨 Alerta de TradingView\n"
        f"{mensaje_alerta}\n"
        f"Par: {par}\n"
        f"Precio: {precio}\n"
        f"Temporalidad: {temporalidad}\n"
        f"Hora: {hora}"
    )
    message = data.get("message")
    if not message:
        try:
            message = f"📢 Alerta TradingView:\n```{json.dumps(data, ensure_ascii=False, indent=2)}```"
        except Exception as e:
            message = f"📢 Alerta TradingView (sin datos legibles). Error: {e}"

    ok, detail = send_telegram(message)
    return jsonify({"ok": ok, "detail": detail}), (200 if ok else 500)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Render te da PORT
    app.run(host="0.0.0.0", port=port)
