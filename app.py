import os
from flask import Flask, render_template

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = "dragon_bot_super_secret"

# Rota 1: Landing Page (Página de Vendas)
@app.route('/')
def landing():
    return render_template('landing.html')

# Rota 2: Login (Para quem já é cliente)
@app.route('/login')
def login():
    return render_template('login.html')

# Rota 3: Cadastro (Página para onde a Kirvano envia o cliente após pagar)
@app.route('/cadastro')
def cadastro():
    return render_template('cadastro.html')

# Rota 4: Dashboard (Onde o robô será construído)
@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
