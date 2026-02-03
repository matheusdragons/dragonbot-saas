import asyncio
import json
import os
import websockets
from flask import Flask, render_template
from flask_sock import Sock

# Pega o caminho exato onde o app.py está rodando
base_dir = os.path.abspath(os.path.dirname(__file__))
# Força o Flask a olhar para a pasta 'templates' no local correto
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
                    if data.get("action") == "buy": data["subscribe"] = 1
                    await deriv_ws.send(json.dumps(data))
            async def backward():
                async for msg in deriv_ws:
                    # Isso garante que Wins/Losses e Saldo cheguem ao painel
                    await client_ws.send(msg)
            await asyncio.gather(forward(), backward())
    except Exception as e:
        print(f"Erro de conexão: {e}")

@sock.route('/ws')
def handle_ws(ws):
    asyncio.run(deriv_proxy(ws))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
