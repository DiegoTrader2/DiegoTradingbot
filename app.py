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
            # Determinar el lado opuesto para cerrar
            side = "Sell" if current_position == "Buy" else "Buy"

            # === Obtener el precio actual del par ===
            ticker_response = session.get(
                "https://api-testnet.bybit.com/v5/market/tickers",
                params={"category": "linear", "symbol": symbol}
            )
            price = float(ticker_response.json()["result"]["list"][0]["lastPrice"])

            # === Calcular la misma cantidad que en la apertura ===
            investment_usdt = 5  # Mismo monto que en open_position()
            qty = round(investment_usdt / price, 6)

            # === Cerrar con orden de mercado ===
            order = session.place_order(
                category="linear",
                symbol=symbol,
                side=side,
                orderType="Market",
                qty=qty,
                timeInForce="GoodTillCancel"
            )

            # === Calcular ganancia o pérdida ===
            if position_entry_price:
                exit_price = float(order["result"]["orderPrice"]) if order["result"].get("orderPrice") else price
                pnl_percent = ((exit_price - position_entry_price) / position_entry_price) * 100
                if current_position == "Sell":
                    pnl_percent *= -1  # Ajustar si era una posición corta

                # === Detectar motivo de cierre ===
                take_profit_pct = 3.0
                stop_loss_pct = 1.5

                if pnl_percent >= take_profit_pct - 0.1:
                    reason = "✅ Take Profit alcanzado"
                elif pnl_percent <= -stop_loss_pct + 0.1:
                    reason = "🛑 Stop Loss ejecutado"
                else:
                    reason = "📉 Cierre manual o por alerta"

                pnl_msg = f"{reason}\n💰 Resultado: {pnl_percent:.2f}%"
            else:
                pnl_msg = "ℹ️ No se pudo obtener el precio de entrada para calcular resultado."

            # === Enviar mensaje a Telegram ===
            send_telegram_message(f"❌ Posición cerrada en {symbol}\n{pnl_msg}")

            # Limpiar posición actual
            current_position = None
            position_entry_price = None

            return order

        else:
            send_telegram_message("ℹ️ No hay posición abierta para cerrar.")
            return None

    except Exception as e:
        send_telegram_message(f"⚠️ Error al cerrar posición: {e}")
        return None
        
# === Endpoint para recibir alertas desde TradingView ===
@app.route("/webhook", methods=["POST"])
def webhook():
    global current_position

    try:
        data = request.get_json()

        # === Validar datos recibidos ===
        if not data or "signal" not in data or "symbol" not in data:
            return jsonify({"status": "error", "message": "Datos incompletos"}), 400

        signal = data["signal"].upper()
        symbol = data["symbol"].upper()

        send_telegram_message(f"📩 Alerta recibida: {signal} en {symbol}")

        # === Lógica de ejecución según señal ===
        if signal == "BUY":
            if current_position == "Buy":
                send_telegram_message("⚠️ Ya hay una posición BUY abierta, no se abre otra.")
            elif current_position == "Sell":
                send_telegram_message("🔄 Señal contraria detectada: cerrando posición SELL antes de abrir BUY.")
                close_position(symbol)
                open_position(signal, symbol)
            else:
                open_position(signal, symbol)

        elif signal == "SELL":
            if current_position == "Sell":
                send_telegram_message("⚠️ Ya hay una posición SELL abierta, no se abre otra.")
            elif current_position == "Buy":
                send_telegram_message("🔄 Señal contraria detectada: cerrando posición BUY antes de abrir SELL.")
                close_position(symbol)
                open_position(signal, symbol)
            else:
                open_position(signal, symbol)

        elif signal == "CLOSE":
            send_telegram_message(f"🚪 Señal de cierre recibida para {symbol}")
            close_position(symbol)

        else:
            send_telegram_message(f"⚠️ Señal desconocida: {signal}")

        return jsonify({"status": "ok", "message": "Alerta procesada"}), 200

    except Exception as e:
        send_telegram_message(f"⚠️ Error en webhook: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
