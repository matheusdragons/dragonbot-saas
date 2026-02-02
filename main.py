import os
import json
import asyncio
import websockets
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI()

# CONFIGURAÇÃO DE DIRETÓRIOS
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates") # Onde está seu index.html
STATIC_DIR = os.path.join(BASE_DIR, "static")       # Onde está sua logo.jpg

# Servir a página principal
@app.get("/")
async def inicial():
    index_path = os.path.join(TEMPLATES_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"error": "index.html nao encontrado na pasta templates"}

# Montar a pasta static para a logo
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    # Conexão direta com a Deriv (App ID padrão)
    deriv_ws_url = "wss://ws.binaryws.com/websockets/v3?app_id=1089"
    
    try:
        async with websockets.connect(deriv_ws_url) as deriv_ws:
            # Escuta a Deriv e manda para o seu navegador
            async def escutar_deriv():
                try:
                    async for msg in deriv_ws:
                        await websocket.send_text(msg)
                except:
                    pass

            asyncio.create_task(escutar_deriv())

            # Escuta o seu navegador e manda para a Deriv
            while True:
                data = await websocket.receive_text()
                msg = json.loads(data)
                
                if msg.get("action") == "auth":
                    await deriv_ws.send(json.dumps({"authorize": msg["token"]}))
                    await deriv_ws.send(json.dumps({"balance": 1, "subscribe": 1}))
                
                elif msg.get("action") == "watch":
                    await deriv_ws.send(json.dumps({"ticks": "R_100", "subscribe": 1}))
                    await deriv_ws.send(json.dumps({"proposal_open_contract": 1, "subscribe": 1}))
                
                elif msg.get("action") == "buy":
                    await deriv_ws.send(json.dumps({
                        "buy": 1,
                        "price": float(msg["stake"]),
                        "parameters": {
                            "amount": float(msg["stake"]),
                            "basis": "stake",
                            "contract_type": "DIGITDIFF",
                            "currency": "USD",
                            "duration": 1,
                            "duration_unit": "t",
                            "symbol": "R_100",
                            "barrier": "7"
                        }
                    }))
    except Exception as e:
        print(f"Erro: {e}")
