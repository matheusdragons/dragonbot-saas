import asyncio
import json
import os
import websockets
from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

async def deriv_proxy(client_ws):
    uri = "wss://ws.binaryws.com/websockets/v3?app_id=1089"
    async with websockets.connect(uri) as deriv_ws:
        async def forward_to_deriv():
            try:
                async for message in client_ws:
                    data = json.loads(message)
                    if data.get("action") == "auth":
                        await deriv_ws.send(json.dumps({"authorize": data["token"]}))
                    elif data.get("action") == "watch":
                        await deriv_ws.send(json.dumps({"ticks": "R_100"}))
                        await deriv_ws.send(json.dumps({"balance": 1, "subscribe": 1}))
                    elif data.get("action") == "buy":
                        await deriv_ws.send(json.dumps({
                            "buy": 1, "price": float(data["stake"]),
                            "parameters": {"amount": float(data["stake"]), "basis": "stake",
                            "contract_type": "DIGITDIFF", "currency": "USD",
                            "duration": 1, "duration_unit": "t", "symbol": "R_100", "barrier": "7"},
                            "subscribe": 1
                        }))
                    elif data.get("action") == "balance":
                        await deriv_ws.send(json.dumps({"balance": 1}))
            except: pass

        async def forward_to_client():
            try:
                async for message in deriv_ws:
                    await client_ws.send(message)
            except: pass

        await asyncio.gather(forward_to_deriv(), forward_to_client())

from flask_sock import Sock
sock = Sock(app)

@sock.route('/ws')
def handle_ws(ws):
    asyncio.run(deriv_proxy(ws))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
