from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# Rota da Página de Vendas
@app.route('/')
def landing():
    return render_template('landing.html')

# Rota de Login
@app.route('/login')
def login():
    return render_template('login.html')

# Rota de Cadastro
@app.route('/cadastro')
def cadastro():
    return render_template('cadastro.html')

# Rota do Painel do Robô (Protegida)
@app.route('/dashboard')
def dashboard():
    # Aqui ficará a página em branco para o novo robô
    return render_template('dashboard.html')

if __name__ == '__main__':
    app.run(debug=True)
