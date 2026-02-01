import sqlite3
import os
from flask import Flask, request, render_template, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'dragonbot_secret_key'

# FUNÇÃO QUE CRIA O BANCO ANTES DE TUDO
def init_db():
    conn = sqlite3.connect('vendas.db')
    cursor = conn.cursor()
    # Cria a tabela de vendas necessária para a página admin não travar
    cursor.execute('''CREATE TABLE IF NOT EXISTS vendas 
        (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, email TEXT, status TEXT, valor TEXT, data_hora TEXT)''')
    # Cria a tabela de usuários
    cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios 
        (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE, password TEXT)''')
    conn.commit()
    conn.close()

# CHAMADA OBRIGATÓRIA DA FUNÇÃO
init_db()

@app.route('/')
def home():
    # Render_template no singular conforme o padrão Flask
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
    except Exception as e:
        return f"Erro: {str(e)}", 400

@app.route('/auth', methods=['POST'])
def auth():
    email = request.form.get('email')
    senha = request.form.get('password')
    conn = sqlite3.connect('vendas.db')
    c = conn.cursor()
    # CORREÇÃO: f.fetchone alterado para c.fetchone
    c.execute('SELECT * FROM usuarios WHERE email = ? AND password = ?', (email, senha))
    user = c.fetchone()
    conn.close()
    if user:
        session['user_email'] = email
        return redirect(url_for('robo_interface'))
    return "Login inválido!", 401

if __name__ == '__main__':
    porta = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=porta)
