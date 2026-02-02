import os
import json
import asyncio
import websockets
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse

app = FastAPI()

# Configuração de pastas
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Criar pastas se não existirem
for path in [TEMPLATES_DIR, STATIC_DIR]:
    if not os.path.exists(path):
        os.makedirs(path)

# Servir arquivos estáticos (CSS, Imagens)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# --- ROTAS DAS PÁGINAS ---

@app.get("/")
async def home():
    """Página de entrada do SaaS (Home)"""
    path = os.path.join(TEMPLATES_DIR, "home.html")
    if os.path.exists(path):
        return FileResponse(path)
    return HTMLResponse("<h1>Página Home em construção...</h1><p>Crie o home.html em templates.</p>")

@app.get("/robot")
async def robot_dashboard():
    """Área do Robô"""
    return FileResponse(os.path.join(TEMPLATES_DIR, "index.html"))

# --- MOTOR DE CONEXÃO (PROXY DERIV) ---

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    deriv_url = "wss://ws.binaryws.com/websockets/v3?app_id=1089"
    
    try:
        async with websockets.connect(deriv_url) as deriv_ws:
            # Escuta Deriv -> Navegador
            async def forward_to_client():
                try:
                    async for message in deriv_ws:
                        await websocket.send_text(message)
                except: pass

            asyncio.create_task(forward_to_client())

            # Escuta Navegador -> Deriv
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
                        "buy": 1, "price": float(msg["stake"]),
                        "parameters": {
                            "amount": float(msg["stake"]), "basis": "stake",
                            "contract_type": "DIGITDIFF", "currency": "USD",
                            "duration": 1, "duration_unit": "t", "symbol": "R_100", "barrier": "7"
                        }
                    }))
    except Exception as e:
        print(f"Erro de conexão: {e}")
