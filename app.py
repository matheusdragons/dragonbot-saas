import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "dragon_secret_key_pro_99"

# CONFIGURAÇÃO DO BANCO (PostgreSQL no Railway ou SQLite local)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# MODELO DO USUÁRIO
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    status_assinatura = db.Column(db.String(20), default='inativo')
    validade = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

# --- ROTA DE TESTE (SIMULAÇÃO DE COMPRA) ---
# Acesse: seunome.railway.app/testar-pagamento
@app.route('/testar-pagamento')
def testar_pagamento():
    email_teste = "cliente@teste.com"
    user = User.query.filter_by(email=email_teste).first()
    
    if not user:
        senha_inicial = generate_password_hash('dragon123')
        user = User(
            email=email_teste, 
            password=senha_inicial, 
            status_assinatura='ativo', 
            validade=datetime.utcnow() + timedelta(days=30)
        )
        db.session.add(user)
        db.session.commit()
        return f"<h1>Sucesso!</h1><p>Usuário <b>{email_teste}</b> criado com senha <b>dragon123</b>.</p><a href='/login'>Ir para Login</a>"
    else:
        return f"<h1>Atenção</h1><p>O usuário <b>{email_teste}</b> já existe no banco.</p><a href='/login'>Ir para Login</a>"

# --- ROTAS DE NAVEGAÇÃO ---

@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password, senha):
            session['user_id'] = user.id
            return redirect(url_for('dashboard'))
        
        return "Erro: E-mail ou senha incorretos. <a href='/login'>Tentar novamente</a>"
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    # Se a assinatura expirou, bloqueia
    if user.status_assinatura != 'ativo' or user.validade < datetime.utcnow():
        return "Sua assinatura expirou. <a href='/'>Voltar</a>"
        
    return render_template('dashboard.html')

@app.route('/alterar-senha', methods=['POST'])
def alterar_senha():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    nova_senha = request.form.get('nova_senha')
    user = User.query.get(session['user_id'])
    
    if user and nova_senha:
        user.password = generate_password_hash(nova_senha)
        db.session.commit()
        return "Senha atualizada com sucesso! <a href='/dashboard'>Voltar ao Painel</a>"
    return "Erro ao atualizar.", 400

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('landing'))

# --- WEBHOOK DA KIRVANO ---

@app.route('/webhook-kirvano', methods=['POST'])
def webhook_kirvano():
    data = request.get_json()
    evento = data.get('event')
    payload = data.get('payload', {})
    email_cliente = payload.get('customer', {}).get('email')

    if not email_cliente:
        return jsonify({"status": "error"}), 400

    if evento in ['order_approved', 'subscription_created', 'subscription_renewed']:
        user = User.query.filter_by(email=email_cliente).first()
        if not user:
            senha_inicial = generate_password_hash('dragon123')
            user = User(
                email=email_cliente, 
                password=senha_inicial, 
                status_assinatura='ativo', 
                validade=datetime.utcnow() + timedelta(days=30)
            )
            db.session.add(user)
        else:
            user.status_assinatura = 'ativo'
            user.validade = datetime.utcnow() + timedelta(days=30)
        db.session.commit()

    return jsonify({"status": "success"}), 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
