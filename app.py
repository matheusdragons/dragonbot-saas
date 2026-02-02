import os
import json
import asyncio
import websockets
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse

app = FastAPI()

# Caminhos organizados
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Garante que as pastas existam
for folder in [TEMPLATES_DIR, STATIC_DIR]:
    if not os.path.exists(folder):
        os.makedirs(folder)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# --- ROTAS DO SAAS ---

@app.get("/")
async def landing_page():
    """Página Home do seu site (que vamos deixar linda a seguir)"""
    path = os.path.join(TEMPLATES_DIR, "home.html")
    if os.path.exists(path):
        return FileResponse(path)
    return HTMLResponse("<h1>DragonBot SaaS - Página Home em Construção</h1>")

@app.get("/dashboard")
async def dashboard():
    """O Dashboard do Robô (Layout Perfeito)"""
    return FileResponse(os.path.join(TEMPLATES_DIR, "index.html"))

# --- PONTE DE CONEXÃO DERIV ---

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    # URL oficial da API Deriv
    deriv_url = "wss://ws.binaryws.com/websockets/v3?app_id=1089"
    
    try:
        async with websockets.connect(deriv_url) as deriv_ws:
            # Task: Enviar tudo da Deriv para o Dashboard
            async def forward_to_ui():
                try:
                    async for message in deriv_ws:
                        await websocket.send_text(message)
                except: pass

            asyncio.create_task(forward_to_ui())

            # Loop: Receber comandos do Dashboard e mandar para a Deriv
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
                    # Lógica Digit Diff (Entrada no dígito 7)
                    await deriv_ws.send(json.dumps({
                        "buy": 1, "price": float(msg["stake"]),
                        "parameters": {
                            "amount": float(msg["stake"]), "basis": "stake",
                            "contract_type": "DIGITDIFF", "currency": "USD",
                            "duration": 1, "duration_unit": "t", "symbol": "R_100", "barrier": "7"
                        }
                    }))
    except Exception as e:
        print(f"Erro na conexão: {e}")
