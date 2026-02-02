import os
import json
import asyncio
import websockets
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse

app = FastAPI()

# Definição de pastas
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Cria as pastas caso não existam no GitHub
for pasta in [TEMPLATES_DIR, STATIC_DIR]:
    if not os.path.exists(pasta):
        os.makedirs(pasta)

# Monta a pasta de imagens/logos
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# --- ROTAS DO SAAS ---

@app.get("/")
async def home():
    """Página de entrada (Landing Page)"""
    path = os.path.join(TEMPLATES_DIR, "home.html")
    if os.path.exists(path):
        return FileResponse(path)
    return HTMLResponse("<h1>DragonBot SaaS</h1><p>Home em construção. Acesse /dashboard</p>")

@app.get("/dashboard")
async def dashboard():
    """Página do Robô (Layout Original)"""
    return FileResponse(os.path.join(TEMPLATES_DIR, "index.html"))

# --- CONEXÃO WEBSOCKET (PONTE COM A DERIV) ---

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    # Conecta à Deriv via servidor para evitar bloqueios de IP/Navegador
    deriv_url = "wss://ws.binaryws.com/websockets/v3?app_id=1089"
    
    try:
        async with websockets.connect(deriv_url) as deriv_ws:
            # Envia dados da Deriv para o Dashboard
            async def para_dashboard():
                try:
                    async for mensagem in deriv_ws:
                        await websocket.send_text(mensagem)
                except: pass

            asyncio.create_task(para_dashboard())

            # Recebe comandos do Dashboard e manda para a Deriv
            while True:
                comando = await websocket.receive_text()
                dados = json.loads(comando)
                
                if dados.get("action") == "auth":
                    await deriv_ws.send(json.dumps({"authorize": dados["token"]}))
                    await deriv_ws.send(json.dumps({"balance": 1, "subscribe": 1}))
                
                elif dados.get("action") == "watch":
                    await deriv_ws.send(json.dumps({"ticks": "R_100", "subscribe": 1}))
                    await deriv_ws.send(json.dumps({"proposal_open_contract": 1, "subscribe": 1}))
                
                elif dados.get("action") == "buy":
                    # Estratégia Diferencial (Dígito 7)
                    await deriv_ws.send(json.dumps({
                        "buy": 1, "price": float(dados["stake"]),
                        "parameters": {
                            "amount": float(dados["stake"]), "basis": "stake",
                            "contract_type": "DIGITDIFF", "currency": "USD",
                            "duration": 1, "duration_unit": "t", "symbol": "R_100", "barrier": "7"
                        }
                    }))
    except Exception as e:
        print(f"Erro na ponte: {e}")
