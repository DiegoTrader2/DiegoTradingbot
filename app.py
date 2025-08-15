import os, json, requests
from flask import Flask, request, jsonify

app = Flask(__name__)

TOKEN = os.environ.get("7981038340:AAFvfzCKbMGP_3eW_xACuUaT2uTiszBxQ1Y")        # lo pondremos en Render
CHAT_ID = os.environ.get("7160439359")    # lo pondremos en Render

def send_telegram(text: str):
    if not TOKEN or not CHAT_ID:
        return False, "Faltan TELEGRAM_TOKEN o TELEGRAM_CHAT_ID"
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
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
    # si TradingView manda "message", lo usamos; si no, mandamos todo el JSON
    message = data.get("message")
    if not message:
        message = f"📈 Alerta TradingView:\n<pre>{json.dumps(data, ensure_ascii=False, indent=2)}</pre>"
    ok, detail = send_telegram(message)
    return jsonify({"ok": ok, "detail": detail}), (200 if ok else 500)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))     # Render te da PORT
    app.run(host="0.0.0.0", port=port)
