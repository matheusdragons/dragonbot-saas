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
    uri = "wss://ws.binaryws.com/websockets/v3?app_id=1089"
    try:
        async with websockets.connect(uri) as deriv_ws:
            async def forward():
                async for msg in client_ws:
                    data = json.loads(msg)
                    # TRADUÇÃO DO COMANDO PARA A DERIV
                    if data.get("action") == "auth":
                        await deriv_ws.send(json.dumps({"authorize": data["token"]}))
                    elif data.get("action") == "watch":
                        await deriv_ws.send(json.dumps({"ticks": "R_100"}))
                    else:
                        await deriv_ws.send(json.dumps(data))

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
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
