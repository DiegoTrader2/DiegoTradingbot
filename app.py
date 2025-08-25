from flask import Flask, request
import requests

app = Flask(__name__)

TOKEN = "TELEGRAM_TOKEN"
CHAT_ID = "TELEGRAM_CHAT_ID"

@app.route('/alert', methods=['POST'])
def alert():
    data = request.get_json()
    mensaje = f"""
📢 Alerta de TradingView
Par: {data.get('ticker', 'N/A')}
💬 Mensaje: {data.get('mensaje', 'N/A')}
💲 Precio: {data.get('precio', 'N/A')}
🕒 Hora: {data.get('hora', 'N/A')}
"""
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": mensaje})
    return "OK", 200

if __name__ == "__main__":
    # Esto mantiene el servidor vivo en Render
    app.run(host="0.0.0.0", port=5000)
