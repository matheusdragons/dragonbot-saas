import asyncio
import json
import os
import websockets
from flask import Flask, render_template
from flask_sock import Sock

# Configuração de caminhos para evitar erro 404
base_dir = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=os.path.join(base_dir, 'templates'))
sock = Sock(app)

@app.route('/')
def index():
    return render_template('index.html')

async def deriv_proxy(client_ws):
    # Conexão direta com o servidor da Deriv
    uri = "wss://ws.binaryws.com/websockets/v3?app_id=1089"
    try:
        async with websockets.connect(uri) as deriv_ws:
            async def forward_to_deriv():
                async for message in client_ws:
                    data = json.loads(message)
                    # Adiciona 'subscribe' automaticamente para garantir atualização do painel
                    if data.get("action") == "buy":
                        data["subscribe"] = 1
                    await deriv_ws.send(json.dumps(data))

            async def forward_to_client():
                async for message in deriv_ws:
                    # Repassa saldo, ticks e resultados (WINS/LOSSES) para o index.html
                    await client_ws.send(message)

            await asyncio.gather(forward_to_deriv(), forward_to_client())
    except Exception as e:
        print(f"Erro de conexão: {e}")

@sock.route('/ws')
def handle_ws(ws):
    asyncio.run(deriv_proxy(ws))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
