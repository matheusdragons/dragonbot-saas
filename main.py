import os
import json
import asyncio
import websockets
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

@app.get("/")
async def inicial():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("✅ Cliente conectado ao servidor local")
    
    deriv_ws_url = "wss://ws.binaryws.com/websockets/v3?app_id=1089"
    
    try:
        async with websockets.connect(deriv_ws_url) as deriv_ws:
            async def escutar_deriv():
                try:
                    async for msg in deriv_ws:
                        print(f"📥 Recebido da Deriv: {msg[:100]}...") # Log para ver se algo chega
                        await websocket.send_text(msg)
                except Exception as e:
                    print(f"❌ Erro na escuta da Deriv: {e}")

            asyncio.create_task(escutar_deriv())

            while True:
                texto = await websocket.receive_text()
                dados = json.loads(texto)
                print(f"📤 Enviando para Deriv: {dados['action']}")
                
                if dados["action"] == "auth":
                    await deriv_ws.send(json.dumps({"authorize": dados["token"]}))
                    await deriv_ws.send(json.dumps({"balance": 1, "subscribe": 1}))
                
                elif dados["action"] == "watch":
                    await deriv_ws.send(json.dumps({"ticks": "R_100", "subscribe": 1}))
                    await deriv_ws.send(json.dumps({"proposal_open_contract": 1, "subscribe": 1}))
                
                elif dados["action"] == "buy":
                    payload = {
                        "buy": 1,
                        "price": float(dados["stake"]),
                        "parameters": {
                            "amount": float(dados["stake"]),
                            "basis": "stake",
                            "contract_type": "DIGITDIFF",
                            "currency": "USD",
                            "duration": 1,
                            "duration_unit": "t",
                            "symbol": "R_100",
                            "barrier": "7" 
                        }
                    }
                    await deriv_ws.send(json.dumps(payload))
    except Exception as e:
        print(f"❌ Erro fatal de conexão: {e}")