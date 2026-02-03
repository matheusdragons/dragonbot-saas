import asyncio
import json
import os
import websockets
from flask import Flask, render_template
from flask_sock import Sock

base_dir = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=os.path.join(base_dir, 'templates'))
sock = Sock(app)

@app.route('/')
def index():
    return render_template('index.html')

async def deriv_proxy(client_ws):
    # App ID 1089 é o padrão, mas você pode usar o seu se tiver um
    uri = "wss://ws.binaryws.com/websockets/v3?app_id=1089"
    try:
        async with websockets.connect(uri) as deriv_ws:
            async def forward():
                async for msg in client_ws:
                    data = json.loads(msg)
                    # Traduz o comando do seu HTML para o que a Deriv entende
                    if data.get("action") == "auth":
                        await deriv_ws.send(json.dumps({"authorize": data["token"]}))
                    elif data.get("action") == "watch":
                        await deriv_ws.send(json.dumps({"ticks": "R_100"}))
                        await deriv_ws.send(json.dumps({"forget_all": "ticks"}))
                    elif data.get("action") == "buy":
                        # Garante que a Deriv responda com o resultado do contrato
                        buy_data = {
                            "buy": 1,
                            "price": data["stake"],
                            "parameters": {
                                "amount": data["stake"],
                                "basis": "stake",
                                "contract_type": "DIGITDIFF",
                                "currency": "USD",
                                "duration": 1,
                                "duration_unit": "t",
                                "symbol": "R_100",
                                "barrier": "7"
                            },
                            "subscribe": 1
                        }
                        await deriv_ws.send(json.dumps(buy_data))
                    else:
                        await deriv_ws.send(msg)
            
            async def backward():
                async for msg in deriv_ws:
                    await client_ws.send(msg)
            
            await asyncio.gather(forward(), backward())
    except Exception as e:
        print(f"Erro: {e}")

@sock.route('/ws')
def handle_ws(ws):
    asyncio.run(deriv_proxy(ws))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
