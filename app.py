import asyncio
import json
import os
import websockets
from flask import Flask, render_template
from flask_sock import Sock

# Pega o caminho real de onde o arquivo app.py está
base_dir = os.path.dirname(os.path.abspath(__file__))
template_dir = os.path.join(base_dir, 'templates')

app = Flask(__name__, template_folder=template_dir)
sock = Sock(app)

@app.route('/')
def index():
    # Isso vai nos dizer no LOG se a pasta realmente existe
    if not os.path.exists(template_dir):
        print(f"ERRO: Pasta templates não encontrada em {template_dir}")
    return render_template('index.html')

async def deriv_proxy(client_ws):
    uri = "wss://ws.binaryws.com/websockets/v3?app_id=1089"
    try:
        async with websockets.connect(uri) as deriv_ws:
            async def forward_to_deriv():
                async for message in client_ws:
                    await deriv_ws.send(message)
            async def forward_to_client():
                async for message in deriv_ws:
                    # REPASSA RESULTADOS PARA ATUALIZAR SALDO E PAINÉIS
                    await client_ws.send(message)
            await asyncio.gather(forward_to_deriv(), forward_to_client())
    except: pass

@sock.route('/ws')
def handle_ws(ws):
    asyncio.run(deriv_proxy(ws))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
