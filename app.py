import asyncio
import json
import os
import websockets
from flask import Flask, render_template
from flask_sock import Sock

app = Flask(__name__)
sock = Sock(app)

@app.route('/')
def index():
    # Isso verifica se a pasta templates existe e o que tem dentro dela
    if not os.path.exists('templates'):
        return "ERRO: Pasta 'templates' não encontrada. Verifique se o nome está todo em minúsculo no GitHub.", 404
    
    files = os.listdir('templates')
    if 'index.html' not in files:
        return f"ERRO: 'index.html' não encontrado dentro da pasta. Arquivos vistos: {files}", 404

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
                    # Garante o repasse para atualizar saldo e painéis
                    await client_ws.send(message)
            await asyncio.gather(forward_to_deriv(), forward_to_client())
    except: pass

@sock.route('/ws')
def handle_ws(ws):
    asyncio.run(deriv_proxy(ws))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
