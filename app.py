import asyncio
import json
import os
import websockets
from flask import Flask, render_template
from flask_sock import Sock

# Garante que o Flask encontre a sua interface original
base_dir = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=os.path.join(base_dir, 'templates'))
sock = Sock(app)

@app.route('/')
def index():
    return render_template('index.html')

async def deriv_proxy(client_ws):
    uri = "wss://ws.binaryws.com/websockets/v3?app_id=1089"
    try:
        async with websockets.connect(uri) as deriv_ws:
            async def forward():
                async for msg in client_ws:
                    data = json.loads(msg)
                    # Força a inscrição para que o painel receba os lucros/perdas
                    if data.get("action") == "buy": data["subscribe"] = 1
                    await deriv_ws.send(json.dumps(data))
            async def backward():
                async for msg in deriv_ws:
                    # Repassa saldo e resultados para o dashboard
                    await client_ws.send(msg)
            await asyncio.gather(forward(), backward())
    except: pass

@sock.route('/ws')
def handle_ws(ws):
    asyncio.run(deriv_proxy(ws))

if __name__ == '__main__':
    # PORTA DINÂMICA: Essencial para o Railway parar de dar 404
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
