import os
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = "chave_secreta_para_seguranca" # Mude isso depois

# 1. ROTA: Landing Page (Página de Vendas)
@app.route('/')
def landing():
    return render_template('landing.html')

# 2. ROTA: Login
@app.route('/login')
def login():
    return render_template('login.html')

# 3. ROTA: Cadastro (Redireciona após a compra na Kirvano)
@app.route('/cadastro')
def cadastro():
    return render_template('cadastro.html')

# 4. ROTA: Dashboard (Onde o robô vai morar)
@app.route('/dashboard')
def dashboard():
    # Aqui verificaremos se o usuário está logado no futuro
    return render_template('dashboard.html')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
