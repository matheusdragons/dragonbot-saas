import asyncio
import json
import os
import websockets
from flask import Flask, render_template
from flask_sock import Sock

app = Flask(__name__, template_folder='templates')
sock = Sock(app)

@app.route('/')
def index():
    return render_template('index.html')

async def deriv_proxy(client_ws):
    uri = "wss://ws.binaryws.com/websockets/v3?app_id=1089" # App ID padrão
    async with websockets.connect(uri) as deriv_ws:
        async def forward():
            async for msg in client_ws:
                data = json.loads(msg)
                # Traduz comandos do seu HTML para a Deriv
                if data.get("action") == "auth":
                    await deriv_ws.send(json.dumps({"authorize": data["token"]}))
                elif data.get("action") == "watch":
                    await deriv_ws.send(json.dumps({"ticks": "R_100"}))
                elif data.get("action") == "buy":
                    buy_payload = {
                        "buy": 1, "price": data["stake"],
                        "parameters": {
                            "amount": data["stake"], "basis": "stake",
                            "contract_type": "DIGITDIFF", "currency": "USD",
                            "duration": 1, "duration_unit": "t",
                            "symbol": "R_100", "barrier": "7"
                        }, "subscribe": 1
                    }
                    await deriv_ws.send(json.dumps(buy_payload))
                else:
                    await deriv_ws.send(json.dumps(data))

        async def backward():
            async for msg in deriv_ws:
                await client_ws.send(msg)

        await asyncio.gather(forward(), backward())

@sock.route('/ws')
def handle_ws(ws):
    asyncio.run(deriv_proxy(ws))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
