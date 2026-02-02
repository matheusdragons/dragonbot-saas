import sqlite3
import os
from flask import Flask, request, render_template, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'dragonbot_secret_key'

# --- INICIALIZAÇÃO DO BANCO DE DADOS ---
def init_db():
    conn = sqlite3.connect('vendas.db')
    cursor = conn.cursor()
    # Tabela para logs da Kirvano
    cursor.execute('''CREATE TABLE IF NOT EXISTS vendas 
        (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, email TEXT, status TEXT, valor TEXT, data_hora TEXT)''')
    # Tabela de usuários do sistema
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
    # Verifica se o usuário está logado na sessão
    if 'user_email' not in session:
        return redirect(url_for('login_page'))
    return render_template('index.html')

# --- LÓGICA DE CADASTRO E LOGIN ---

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
        return "Conta criada! <a href='/login'>Clique aqui para logar</a>"
    except:
        return "Erro: Este e-mail já existe.", 400

@app.route('/auth', methods=['POST'])
def auth():
    email = request.form.get('email')
    senha = request.form.get('password')
    conn = sqlite3.connect('vendas.db')
    c = conn.cursor()
    # Validação de credenciais
    c.execute('SELECT * FROM usuarios WHERE email = ? AND password = ?', (email, senha))
    user = c.fetchone()
    conn.close()

    if user:
        session['user_email'] = email
        return redirect(url_for('robo_interface'))
    return "Login inválido!", 401

# --- WEBHOOK DA KIRVANO ---

@app.route('/webhook-kirvano', methods=['POST'])
def webhook():
    d = request.get_json()
    if d:
        cli = d.get('customer', {})
        email_cliente = cli.get('email')
        status_venda = d.get('status')
        
        conn = sqlite3.connect('vendas.db')
        c = conn.cursor()
        
        # Registra a venda
        c.execute('INSERT INTO vendas (nome, email, status, valor, data_hora) VALUES (?, ?, ?, ?, ?)',
                  (cli.get('name'), email_cliente, status_venda, d.get('total_price'), d.get('created_at')))
        
        # Cria usuário automático para vendas aprovadas
        if status_venda == 'approved':
            try:
                c.execute('INSERT INTO usuarios (email, password) VALUES (?, ?)', (email_cliente, "mudar123"))
            except sqlite3.IntegrityError:
                pass
        
        conn.commit()
        conn.close()
    return "OK", 200

if __name__ == '__main__':
    porta = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=porta)
