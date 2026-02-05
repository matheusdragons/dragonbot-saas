import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import uuid

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dragon_secret_key_pro_99')

# CONFIGURAÇÃO DO BANCO
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
    session_token = db.Column(db.String(100), unique=True) # Bloqueio de Multiacesso

with app.app_context():
    db.create_all()

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
            # Gera novo token de sessão para derrubar outros acessos
            novo_token = str(uuid.uuid4())
            user.session_token = novo_token
            db.session.commit()
            
            session['user_id'] = user.id
            session['session_token'] = novo_token
            return redirect(url_for('dashboard'))
        
        # Se falhar, mostra erro na página de login
        return render_template('login.html', erro="E-mail ou senha inválidos. Verifique seus dados e tente novamente.")
    
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    
    # Validação de Multiacesso
    if session.get('session_token') != user.session_token:
        session.clear()
        return "Sua conta foi conectada em outro local. <a href='/login'>Entrar novamente</a>"

    # Validação de Assinatura
    if user.status_assinatura != 'ativo' or user.validade < datetime.utcnow():
        return "Assinatura expirada ou inativa. Entre em contato com o suporte. <a href='/'>Voltar</a>"
        
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
    return "Erro ao processar alteração.", 400

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('landing'))

# --- WEBHOOK OFICIAL (INTEGRAÇÃO KIRVANO) ---

@app.route('/webhook-kirvano', methods=['POST'])
def webhook_kirvano():
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "No data"}), 400

    evento = data.get('event')
    payload = data.get('payload', {})
    email_cliente = payload.get('customer', {}).get('email')

    if email_cliente and evento in ['order_approved', 'subscription_created', 'subscription_renewed']:
        user = User.query.filter_by(email=email_cliente).first()
        
        if not user:
            # Criação automática do cliente
            senha_padrao = generate_password_hash('dragon123')
            user = User(
                email=email_cliente, 
                password=senha_padrao, 
                status_assinatura='ativo', 
                validade=datetime.utcnow() + timedelta(days=30)
            )
            db.session.add(user)
        else:
            # Renovação de acesso
            user.status_assinatura = 'ativo'
            user.validade = datetime.utcnow() + timedelta(days=30)
            
        db.session.commit()
        return jsonify({"status": "success"}), 200

    return jsonify({"status": "ignored"}), 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
