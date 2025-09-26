import os
import requests
from flask import Flask, request, jsonify
from pybit.unified_trading import HTTP

# Cargar variables de entorno
from dotenv import load_dotenv
load_dotenv()

# Credenciales
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
BYBIT_API_KEY = os.getenv("BYBIT_API_KEY")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET")

# Inicializar Bybit
session = HTTP(
    testnet=True,  # True si usás cuenta demo
    api_key=BYBIT_API_KEY,
    api_secret=BYBIT_API_SECRET
)

# Flask
app = Flask(__name__)

# Función para enviar mensaje a Telegram
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    requests.post(url, json=payload)

# Función para abrir orden
def place_order(symbol, side, qty=100):
    try:
        order = session.place_order(
            category="linear",
            symbol=symbol,
            side=side,
            orderType="Market",
            qty=qty,
            timeInForce="GTC"
        )
        send_telegram_message(f"✅ Orden enviada: {side} {qty} {symbol}")
        return order
    except Exception as e:
        send_telegram_message(f"❌ Error al enviar orden: {e}")
        return None

# Función para cerrar orden y reportar ganancia/pérdida
def close_position(symbol, side):
    try:
        opposite = "Sell" if side == "Buy" else "Buy"

        # Cierra posición
        session.place_order(
            category="linear",
            symbol=symbol,
            side=opposite,
            orderType="Market",
            qty=100,
            timeInForce="GTC"
        )

        # Consultar PNL
        result = session.get_closed_pnl(category="linear", symbol=symbol, limit=1)
        if "result" in result and result["result"]["list"]:
            last_trade = result["result"]["list"][0]
            realised_pnl = last_trade["realisedPnl"]
            send_telegram_message(
                f"📊 Operación cerrada en {symbol}\nGanancia/Pérdida: {realised_pnl} USDT"
            )
        else:
            send_telegram_message("⚠️ Operación cerrada pero no encontré PNL.")

    except Exception as e:
        send_telegram_message(f"❌ Error al cerrar operación: {e}")

# Webhook para recibir alertas de TradingView
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    if not data:
        return jsonify({"error": "No se recibieron datos"}), 400

    try:
        symbol = data.get("symbol", "BTCUSDT")
        action = data.get("action")

        if action == "BUY":
            place_order(symbol, "Buy")
        elif action == "SELL":
            close_position(symbol, "Buy")  # Cierra si estaba en Buy
            place_order(symbol, "Sell")
        else:
            send_telegram_message(f"⚠️ Acción desconocida: {action}")

        return jsonify({"status": "ok"}), 200

    except Exception as e:
        send_telegram_message(f"❌ Error en webhook: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(port=5000)
