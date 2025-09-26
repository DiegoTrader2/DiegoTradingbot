import os
from flask import Flask, request, jsonify
from pybit.unified_trading import HTTP
import requests

# Cargar variables de entorno
BYBIT_API_KEY = os.getenv("BYBIT_API_KEY")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Cliente Bybit (modo demo)
session = HTTP(
    testnet=True,
    api_key=BYBIT_API_KEY,
    api_secret=BYBIT_API_SECRET
)

app = Flask(__name__)

# Variables globales
current_position = None  # Guardar la posición abierta
position_entry_price = None  # Precio de entrada de la posición

# Función para enviar mensajes a Telegram
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    requests.post(url, json=payload)

# Función para abrir operación
def open_position(signal, symbol, amount):
    global current_position, position_entry_price

    try:
        side = "Buy" if signal == "BUY" else "Sell"
        qty = float(amount.replace("USDT", "").strip()) / 1000  # Ejemplo: BTC ≈ 1000 USDT

        order = session.place_order(
            category="linear",
            symbol=symbol,
            side=side,
            orderType="Market",
            qty=qty,
            timeInForce="GoodTillCancel",
            takeProfit=3.0,    # TP 3%
            stopLoss=1.5       # SL 1.5%
        )

        current_position = side
        position_entry_price = float(order["result"]["orderPrice"]) if order["result"]["orderPrice"] else None

        send_telegram_message(f"✅ Operación {side} abierta en {symbol} con {amount}")
        return order

    except Exception as e:
        send_telegram_message(f"⚠️ Error al abrir posición: {e}")
        return None

# Función para cerrar operación
def close_position(symbol):
    global current_position, position_entry_price

    try:
        if current_position:
            side = "Sell" if current_position == "Buy" else "Buy"

            # Cerrar con orden de mercado
            order = session.place_order(
                category="linear",
                symbol=symbol,
                side=side,
                orderType="Market",
                qty=0.1,  # Se puede mejorar para que detecte el tamaño real
                timeInForce="GoodTillCancel"
            )

            # Calcular ganancia/perdida
            if position_entry_price:
                exit_price = float(order["result"]["orderPrice"]) if order["result"]["orderPrice"] else position_entry_price
                pnl = ((exit_price - position_entry_price) / position_entry_price) * 100
                pnl_msg = f"📊 Resultado: {pnl:.2f}%"
            else:
                pnl_msg = "📊 Resultado no disponible (precio de entrada desconocido)."

            send_telegram_message(f"❌ Posición cerrada en {symbol}\n{pnl_msg}")

            current_position = None
            position_entry_price = None

            return order
        else:
            send_telegram_message("ℹ️ No hay posición abierta para cerrar.")
            return None
    except Exception as e:
        send_telegram_message(f"⚠️ Error al cerrar posición: {e}")
        return None

# Endpoint para recibir alertas de TradingView
@app.route("/webhook", methods=["POST"])
def webhook():
    global current_position

    data = request.json
    signal = data.get("signal")
    symbol = data.get("pair")
    amount = data.get("amount")

    if not signal or not symbol:
        return jsonify({"status": "error", "message": "Faltan datos"}), 400

    if not current_position:
        # No hay posición → abrir nueva
        open_position(signal, symbol, amount)
    elif (signal == "BUY" and current_position == "Buy") or (signal == "SELL" and current_position == "Sell"):
        # Mismo sentido → ignorar
        send_telegram_message(f"ℹ️ Señal repetida {signal}, operación ignorada.")
    else:
        # Señal contraria → cerrar y abrir
        close_position(symbol)
        open_position(signal, symbol, amount)

    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
