import os
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = "dragon_secret_key" # Chave para sessões de usuário

# 1. Rota da Landing Page (Página de Vendas)
@app.route('/')
def landing():
    return render_template('landing.html')

# 2. Rota de Login
@app.route('/login')
def login():
    return render_template('login.html')

# 3. Rota de Cadastro (Acessada após a compra)
@app.route('/cadastro')
def cadastro():
    return render_template('cadastro.html')

# 4. Rota do Dashboard (Onde o robô ficará futuramente)
@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
