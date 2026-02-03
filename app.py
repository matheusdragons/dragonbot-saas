import asyncio
import json
import os
import websockets
from flask import Flask, render_template, send_from_directory
from flask_sock import Sock

# Forçamos o Flask a entender que a pasta de templates está no mesmo diretório
base_dir = os.path.abspath(os.path.dirname(__file__))
template_dir = os.path.join(base_dir, 'templates')

app = Flask(__name__, template_folder=template_dir)
sock = Sock(app)

@app.route('/')
def index():
    # Verificação de segurança: se a pasta ou arquivo não existirem, avisamos o erro real
    if not os.path.exists(template_dir):
        return f"ERRO CRÍTICO: A pasta 'templates' não foi encontrada no diretório: {base_dir}", 500
    
    index_path = os.path.join(template_dir, 'index.html')
    if not os.path.exists(index_path):
        return f"ERRO CRÍTICO: O arquivo 'index.html' não existe dentro da pasta 'templates'.", 404

    return render_template('index.html')

async def deriv_proxy(client_ws):
    uri = "wss://ws.binaryws.com/websockets/v3?app_id=1089"
    try:
        async with websockets.connect(uri) as deriv_ws:
            async def forward_to_deriv():
                async for message in client_ws:
                    await deriv_ws.send(message)
            async def forward_to_client():
                async for message in deriv_ws:
                    await client_ws.send(message)
            await asyncio.gather(forward_to_deriv(), forward_to_client())
    except Exception as e:
        print(f"Erro de conexão: {e}")

@sock.route('/ws')
def handle_ws(ws):
    asyncio.run(deriv_proxy(ws))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
