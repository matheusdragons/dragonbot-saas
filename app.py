import asyncio
import json
import os
import websockets
from flask import Flask, render_template
from flask_sock import Sock

# Forçamos o Flask a encontrar a pasta templates no diretório atual
app = Flask(__name__, template_folder='templates')
sock = Sock(app)

@app.route('/')
def index():
    return render_template('index.html')

async def deriv_proxy(client_ws):
    uri = "wss://ws.binaryws.com/websockets/v3?app_id=1089"
    async with websockets.connect(uri) as deriv_ws:
        async def forward_to_deriv():
            try:
                async for message in client_ws:
                    await deriv_ws.send(message)
            except: pass

        async def forward_to_client():
            try:
                async for message in deriv_ws:
                    # ESTA LINHA É O QUE FAZ O SALDO E PAINÉIS FUNCIONAREM
                    await client_ws.send(message)
            except: pass

        await asyncio.gather(forward_to_deriv(), forward_to_client())

@sock.route('/ws')
def handle_ws(ws):
    asyncio.run(deriv_proxy(ws))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
