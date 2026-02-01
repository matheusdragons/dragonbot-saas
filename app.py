import sqlite3
import os
from flask import Flask, request, render_template, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'dragonbot_secret_key'

# --- INICIALIZAÇÃO DO BANCO DE DADOS ---
def init_db():
    conn = sqlite3.connect('vendas.db')
    cursor = conn.cursor()
    # Cria tabela para o Webhook da Kirvano
    cursor.execute('''CREATE TABLE IF NOT EXISTS vendas 
        (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, email TEXT, status TEXT, valor TEXT, data_hora TEXT)''')
    # Cria tabela para usuários do sistema
    cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios 
        (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE, password TEXT)''')
    conn.commit()
    conn.close()

# Executa a criação das tabelas antes do app começar a rodar
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

# --- NOVA ROTA PARA VER AS VENDAS (WEBHOOK TESTE) ---
@app.route('/ver-vendas')
def ver_vendas():
    # Apenas para você conferir se os dados da Kirvano estão chegando
    conn = sqlite3.connect('vendas.db')
    c = conn.cursor()
    c.execute('SELECT * FROM vendas ORDER BY id DESC')
    lista_vendas = c.fetchall()
    conn.close()
    
    # Retorna uma lista simples no navegador para conferência
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
    # CORREÇÃO: Usando 'c.fetchone()' para validar o login
    c.execute('SELECT * FROM usuarios WHERE email = ? AND password = ?', (email, senha))
    user = c.fetchone()
    conn.close()

    if user:
        session['user_email'] = email
        return redirect(url_for('robo_interface'))
    return "Login inválido!", 401

# --- WEBHOOK KIRVANO ---
@app.route('/webhook-kirvano', methods=['POST'])
def webhook():
    d = request.get_json()
    if d:
        cli = d.get('customer', {})
        conn = sqlite3.connect('vendas.db')
        c = conn.cursor()
        # Salva os dados enviados pela Kirvano
        c.execute('INSERT INTO vendas (nome, email, status, valor, data_hora) VALUES (?, ?, ?, ?, ?)',
                  (cli.get('name'), cli.get('email'), d.get('status'), d.get('total_price'), d.get('created_at')))
        conn.commit()
        conn.close()
    return "OK", 200

if __name__ == '__main__':
    # Configuração de porta para o Railway
    porta = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=porta)
