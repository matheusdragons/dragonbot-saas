import asyncio
import json
import os
import websockets
from flask import Flask, render_template
from flask_sock import Sock

# Pega o caminho absoluto da pasta onde o app.py está
base_dir = os.path.dirname(os.path.abspath(__file__))
# Força o Flask a olhar para a pasta 'templates' no lugar certo
app = Flask(__name__, template_folder=os.path.join(base_dir, 'templates'))
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
                    # ISSO GARANTE A ATUALIZAÇÃO DO SALDO E PAINÉIS
                    await client_ws.send(message)
            except: pass
        await asyncio.gather(forward_to_deriv(), forward_to_client())

@sock.route('/ws')
def handle_ws(ws):
    asyncio.run(deriv_proxy(ws))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
