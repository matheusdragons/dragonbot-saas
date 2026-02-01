import sqlite3
import os
from flask import Flask, request, render_template, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'dragonbot_secret_key'

# --- INICIALIZAÇÃO DO BANCO DE DADOS ---
def init_db():
    conn = sqlite3.connect('vendas.db')
    cursor = conn.cursor()
    # Tabela para registrar o histórico de webhooks da Kirvano
    cursor.execute('''CREATE TABLE IF NOT EXISTS vendas 
        (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, email TEXT, status TEXT, valor TEXT, data_hora TEXT)''')
    # Tabela de usuários para login no sistema
    cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios 
        (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE, password TEXT)''')
    conn.commit()
    conn.close()

# Garante que as tabelas existam antes de qualquer acesso
init_db()

# --- ROTAS DE PÁGINAS ---

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/cadastro')
def cadastro_page():
    # Mantemos esta rota caso você queira permitir cadastro manual
    return render_template('cadastro.html')

@app.route('/acesso-liberado')
def robo_interface():
    # Proteção de rota: só acessa se estiver logado
    if 'user_email' not in session:
        return redirect(url_for('login_page'))
    return render_template('index.html')

# --- LÓGICA DE WEBHOOK (AUTOMAÇÃO) ---

@app.route('/webhook-kirvano', methods=['POST'])
def webhook():
    d = request.get_json()
    if d:
        cli = d.get('customer', {})
        email_cliente = cli.get('email')
        status_venda = d.get('status')
        nome_cliente = cli.get('name')
        
        conn = sqlite3.connect('vendas.db')
        c = conn.cursor()
        
        # 1. Registra os dados da venda
        c.execute('INSERT INTO vendas (nome, email, status, valor, data_hora) VALUES (?, ?, ?, ?, ?)',
                  (nome_cliente, email_cliente, status_venda, d.get('total_price'), d.get('created_at')))
        
        # 2. Se a venda for aprovada, cria o usuário automaticamente
        if status_venda == 'approved':
            try:
                # O cliente logará com este e-mail e a senha 'mudar123'
                c.execute('INSERT INTO usuarios (email, password) VALUES (?, ?)', (email_cliente, "mudar123"))
            except sqlite3.IntegrityError:
                # Se o e-mail já existir, não faz nada (evita erro 500)
                pass
        
        conn.commit()
        conn.close()
    return "OK", 200

# --- LÓGICA DE AUTENTICAÇÃO ---

@app.route('/auth', methods=['POST'])
def auth():
    email = request.form.get('email')
    senha = request.form.get('password')
    
    conn = sqlite3.connect('vendas.db')
    c = conn.cursor()
    # Verifica se o e-mail e senha batem com o banco
    c.execute('SELECT * FROM usuarios WHERE email = ? AND password = ?', (email, senha))
    user = c.fetchone()
    conn.close()

    if user:
        session['user_email'] = email
        return redirect(url_for('robo_interface'))
    else:
        return "Login inválido! Verifique seu e-mail e senha.", 401

if __name__ == '__main__':
    # Configuração de porta dinâmica para o Railway
    porta = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=porta)
