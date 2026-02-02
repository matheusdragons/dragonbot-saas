import os
import json
import asyncio
import websockets
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse

app = FastAPI()

# Configuração de caminhos para templates e estáticos
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Cria as pastas se não existirem para evitar erros
for folder in [TEMPLATES_DIR, STATIC_DIR]:
    if not os.path.exists(folder):
        os.makedirs(folder)

# Servir arquivos estáticos (logos, css)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# --- ROTAS DO SITE ---

@app.get("/")
async def home():
    """Página de entrada (Landing Page)"""
    path = os.path.join(TEMPLATES_DIR, "home.html")
    if os.path.exists(path):
        return FileResponse(path)
    return HTMLResponse("<h1>Página Home pronta para ser criada!</h1>")

@app.get("/robot")
async def robot_page():
    """O Dashboard do Robô"""
    return FileResponse(os.path.join(TEMPLATES_DIR, "index.html"))

# --- MOTOR DO ROBÔ (WEB SOCKET PROXY) ---

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    # Conexão segura com a Deriv
    deriv_url = "wss://ws.binaryws.com/websockets/v3?app_id=1089"
    
    try:
        async with websockets.connect(deriv_url) as deriv_ws:
            async def deriv_to_browser():
                try:
                    async for message in deriv_ws:
                        await websocket.send_text(message)
                except: pass

            asyncio.create_task(deriv_to_browser())

            while True:
                client_msg = await websocket.receive_text()
                data = json.loads(client_msg)
                
                if data.get("action") == "auth":
                    await deriv_ws.send(json.dumps({"authorize": data["token"]}))
                    await deriv_ws.send(json.dumps({"balance": 1, "subscribe": 1}))
                elif data.get("action") == "watch":
                    await deriv_ws.send(json.dumps({"ticks": "R_100", "subscribe": 1}))
                    await deriv_ws.send(json.dumps({"proposal_open_contract": 1, "subscribe": 1}))
                elif data.get("action") == "buy":
                    await deriv_ws.send(json.dumps({
                        "buy": 1, "price": float(data["stake"]),
                        "parameters": {
                            "amount": float(data["stake"]), "basis": "stake",
                            "contract_type": "DIGITDIFF", "currency": "USD",
                            "duration": 1, "duration_unit": "t", "symbol": "R_100", "barrier": "7"
                        }
                    }))
    except Exception as e:
        print(f"Erro de conexão: {e}")
