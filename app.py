import sqlite3
import os
from flask import Flask, request, render_template, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'dragonbot_secret_key'

# --- INICIALIZAÇÃO DO BANCO DE DADOS ---
def init_db():
    conn = sqlite3.connect('vendas.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS vendas 
        (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, email TEXT, status TEXT, valor TEXT, data_hora TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios 
        (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE, password TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- ROTAS DE NAVEGAÇÃO ---

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/cadastro')
def cadastro_page():
    return render_template('cadastro.html')

@app.route('/acesso-liberado')
def robo_interface():
    if 'user_email' not in session:
        return redirect(url_for('login_page'))
    return render_template('index.html')

@app.route('/ver-vendas')
def ver_vendas():
    conn = sqlite3.connect('vendas.db')
    c = conn.cursor()
    c.execute('SELECT * FROM vendas ORDER BY id DESC')
    lista_vendas = c.fetchall()
    conn.close()
    if not lista_vendas:
        return "Nenhuma venda registrada ainda. Configure o Webhook na Kirvano."
    html = "<h1>Lista de Vendas (Kirvano)</h1><ul>"
    for v in lista_vendas:
        html += f"<li>Nome: {v[1]} | E-mail: {v[2]} | Status: {v[3]} | Valor: {v[4]}</li>"
    html += "</ul><br><a href='/'>Voltar</a>"
    return html

# --- LÓGICA DE AUTENTICAÇÃO ---

@app.route('/registrar_usuario', methods=['POST'])
def registrar():
    email = request.form.get('email')
    senha = request.form.get('password')
    try:
        conn = sqlite3.connect('vendas.db')
        c = conn.cursor()
        c.execute('INSERT INTO usuarios (email, password) VALUES (?, ?)', (email, senha))
        conn.commit()
        conn.close()
        return redirect(url_for('login_page'))
    except:
        return "Erro: E-mail já cadastrado.", 400

@app.route('/auth', methods=['POST'])
def auth():
    email = request.form.get('email')
    senha = request.form.get('password')
    conn = sqlite3.connect('vendas.db')
    c = conn.cursor()
    c.execute('SELECT * FROM usuarios WHERE email = ? AND password = ?', (email, senha))
    user = c.fetchone()
    conn.close()
    if user:
        session['user_email'] = email
        return redirect(url_for('robo_interface'))
    return "Login inválido!", 401

# --- WEBHOOK KIRVANO COM CRIAÇÃO AUTOMÁTICA DE USUÁRIO ---
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
        
        # 1. Registra a venda na tabela de vendas
        c.execute('INSERT INTO vendas (nome, email, status, valor, data_hora) VALUES (?, ?, ?, ?, ?)',
                  (nome_cliente, email_cliente, status_venda, d.get('total_price'), d.get('created_at')))
        
        # 2. Se a venda for aprovada, cria o acesso automático
        if status_venda == 'approved':
            try:
                # Definimos a senha inicial como os 6 primeiros dígitos do e-mail ou uma fixa
                senha_inicial = "mudar123" 
                c.execute('INSERT INTO usuarios (email, password) VALUES (?, ?)', (email_cliente, senha_inicial))
            except sqlite3.IntegrityError:
                # Se o usuário já existir, não faz nada para não dar erro
                pass
        
        conn.commit()
        conn.close()
    return "OK", 200

if __name__ == '__main__':
    porta = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=porta)
