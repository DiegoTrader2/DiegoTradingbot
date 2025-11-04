import os
from flask import Flask, request, jsonify
from pybit.unified_trading import HTTP
import requests

# Cargar variables de entorno
BYBIT_API_KEY = os.getenv("BYBIT_API_KEY")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# ✅ Bloque de verificación
print("DEBUG: Variables de entorno cargadas:")
print("BYBIT_API_KEY:", "✅ OK" if BYBIT_API_KEY else "❌ FALTA")
print("BYBIT_API_SECRET:", "✅ OK" if BYBIT_API_SECRET else "❌ FALTA")
print("TELEGRAM_TOKEN:", "✅ OK" if TELEGRAM_TOKEN else "❌ FALTA")
print("TELEGRAM_CHAT_ID:", "✅ OK" if TELEGRAM_CHAT_ID else "❌ FALTA")

# Cliente Bybit (modo demo)
session = HTTP(
    testnet=True,
    api_key=BYBIT_API_KEY,
    api_secret=BYBIT_API_SECRET
)

# Inicializar Flask
app = Flask(__name__)

# (acá recién podés usar @app.route...)
@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "ok", "message": "Bot activo"}), 200

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
        qty = 0.001 # aproximadamente 68 USDT segun el precio actual de BTC 

        # Crear orden de mercado (sin TP/SL inicial)
        order = session.place_order(
            category="linear",
            symbol=symbol,
            side=side,
            orderType="Market",
            qty=qty,
            timeInForce="GoodTillCancel"
        )

        # Verificar si se ejecutó correctamente
        if "result" not in order or "orderPrice" not in order["result"]:
            send_telegram_message(f"⚠️ No se pudo obtener el precio de entrada para {symbol}. Respuesta: {order}")
            return None

        # Guardar posición actual
        current_position = side
        position_entry_price = float(order["result"]["orderPrice"])

        # ✅ Calcular precios automáticos en base a porcentaje
        take_profit_pct = 3.0   # Porcentaje de ganancia
        stop_loss_pct = 1.5     # Porcentaje de pérdida

        if side == "Buy":
            take_profit_price = position_entry_price * (1 + take_profit_pct / 100)
            stop_loss_price = position_entry_price * (1 - stop_loss_pct / 100)
        else:  # Venta
            take_profit_price = position_entry_price * (1 - take_profit_pct / 100)
            stop_loss_price = position_entry_price * (1 + stop_loss_pct / 100)

        # ✅ Crear órdenes separadas de Take Profit y Stop Loss
        tp_order = session.place_order(
            category="linear",
            symbol=symbol,
            side="Sell" if side == "Buy" else "Buy",
            orderType="Limit",
            qty=qty,
            price=round(take_profit_price, 2),
            timeInForce="GoodTillCancel",
            reduceOnly=True
        )

        sl_order = session.place_order(
            category="linear",
            symbol=symbol,
            side="Sell" if side == "Buy" else "Buy",
            orderType="StopMarket",
            qty=qty,
            triggerDirection=1 if side == "Buy" else 2,
            stopPx=round(stop_loss_price, 2),
            timeInForce="GoodTillCancel",
            reduceOnly=True
        )

        # Enviar confirmación por Telegram
        send_telegram_message(
            f"✅ Operación {side} abierta en {symbol}\n"
            f"💰 Precio entrada: {position_entry_price}\n"
            f"🎯 TP: {round(take_profit_price, 2)} (+{take_profit_pct}%)\n"
            f"🛑 SL: {round(stop_loss_price, 2)} (-{stop_loss_pct}%)"
        )

        return order

    except Exception as e:
        send_telegram_message(f"⚠️ Error al abrir posición: {e}")
        return None
                  
# Función para cerrar operación
def close_position(symbol):
    global current_position, position_entry_price

    try:
        if current_position:
            # Determinar dirección contraria
            side = "Sell" if current_position == "Buy" else "Buy"

            # Obtener último precio de mercado
            ticker = session.get_tickers(category="linear", symbol=symbol)
            market_price = float(ticker["result"]["list"][0]["lastPrice"])

            # Cerrar posición con orden de mercado
            order = session.place_order(
                category="linear",
                symbol=symbol,
                side=side,
                orderType="Market",
                qty=0.001,
                timeInForce="GoodTillCancel"
            )

            # Calcular ganancia o pérdida
            if position_entry_price:
                exit_price = market_price
                pnl_percent = ((exit_price - position_entry_price) / position_entry_price) * 100

                # Si era una posición corta (venta), invertir el signo
                if current_position == "Sell":
                    pnl_percent *= -1

                # Detectar motivo de cierre
                if pnl_percent >= 3.0:
                    reason = "✅ TP alcanzado"
                elif pnl_percent <= -1.5:
                    reason = "🛑 SL ejecutado"
                else:
                    reason = "🔹 Cierre manual o por alerta"

                pnl_msg = f"{reason}\n💰 Resultado: {pnl_percent:.2f}%"
            else:
                pnl_msg = "ℹ️ No se pudo calcular el resultado (precio de entrada desconocido)."

            # Enviar mensaje a Telegram
            send_telegram_message(f"❌ Posición cerrada en {symbol}\n{pnl_msg}")

            # Resetear variables globales
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
@app.route("/webhook",methods=["POST"])
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
