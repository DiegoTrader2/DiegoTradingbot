from flask import Flask, request
import requests
import os
from datetime import datetime

app = Flask(__name__)

# ⚡ Variables de entorno (ponelas en Render)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_message(message: str):
    """Envía un mensaje a Telegram usando la API."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        r = requests.post(url, data=payload)
        r.raise_for_status()
    except Exception as e:
        print("❌ Error enviando mensaje:", e)

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.json
        print("📩 Alerta recibida:", data)

        # Datos que manda TradingView en el mensaje {{...}}
        par = data.get("par", "N/A")
        senal = data.get("senal", "N/A")
        precio = data.get("precio", "N/A")
        temporalidad = data.get("temporalidad", "N/A")
        hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Mensaje final con formato
        mensaje = (
            f"{par}\n"
            f"Señal: {senal}\n"
            f"Precio: {precio}\n"
            f"Temporalidad: {temporalidad}\n"
            f"Hora: {hora}"
        )

        send_telegram_message(mensaje)
        return {"status": "ok"}, 200

    except Exception as e:
        print("❌ Error en webhook:", e)
        return {"status": "error", "message": str(e)}, 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
