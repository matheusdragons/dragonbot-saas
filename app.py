import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "dragon_secret_key_pro"

# CONFIGURAÇÃO DO BANCO DE DATAS (Railway PostgreSQL)
# O Railway fornece a variável DATABASE_URL automaticamente
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# MODELO DO UTILIZADOR (Tabela no Banco de Dados)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    status_assinatura = db.Column(db.String(20), default='inativo') # ativo ou inativo
    validade = db.Column(db.DateTime, default=datetime.utcnow)

# Criar o banco de dados
with app.app_context():
    db.create_all()

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
        
        flash('E-mail ou senha incorretos.')
    return render_template('login.html')

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('password')
        
        # Criptografar senha
        hash_senha = generate_password_hash(senha)
        
        novo_usuario = User(email=email, password=hash_senha, status_assinatura='ativo', validade=datetime.utcnow() + timedelta(days=30))
        db.session.add(novo_usuario)
        db.session.commit()
        
        return redirect(url_for('login'))
    return render_template('cadastro.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    
    # VERIFICAÇÃO DE SEGURANÇA: Só entra se estiver ativo e na validade
    if user.status_assinatura != 'ativo' or user.validade < datetime.utcnow():
        return "Sua assinatura expirou. Por favor, renove o pagamento."
        
    return render_template('dashboard.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('landing'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
