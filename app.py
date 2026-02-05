import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from functools import wraps
import uuid

from config import Config
from models import db, User, TradeHistory

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

with app.app_context():
    db.create_all()

# ==================== DECORADORES ====================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        user = User.query.get(session['user_id'])
        if not user:
            session.clear()
            return redirect(url_for('login'))
        
        if session.get('session_token') != user.session_token:
            session.clear()
            return redirect(url_for('login'))
        
        return f(*args, **kwargs)
    return decorated_function


def subscription_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = User.query.get(session['user_id'])
        if not user.is_active():
            return render_template('erro.html', 
                mensagem="Sua assinatura expirou ou está inativa.",
                botao_texto="Ver Planos",
                botao_link="/#planos")
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = User.query.get(session['user_id'])
        if user.email != Config.ADMIN_EMAIL:
            return "Acesso negado.", 403
        return f(*args, **kwargs)
    return decorated_function

# ==================== ROTAS PÚBLICAS ====================

@app.route('/')
def landing():
    return render_template('landing.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').lower().strip()
        senha = request.form.get('password', '')
        
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password, senha):
            novo_token = str(uuid.uuid4())
            user.session_token = novo_token
            user.ultimo_acesso = datetime.utcnow()
            db.session.commit()
            
            session['user_id'] = user.id
            session['session_token'] = novo_token
            
            if user.email == Config.ADMIN_EMAIL:
                return redirect(url_for('admin_dashboard'))
            
            return redirect(url_for('dashboard'))
        
        return render_template('login.html', erro="E-mail ou senha incorretos.")
    
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('landing'))

# ==================== ROTAS DO USUÁRIO ====================

@app.route('/dashboard')
@login_required
@subscription_required
def dashboard():
    user = User.query.get(session['user_id'])
    return render_template('dashboard.html', user=user)


@app.route('/minha-conta')
@login_required
def minha_conta():
    user = User.query.get(session['user_id'])
    return render_template('conta.html', user=user)


@app.route('/alterar-senha', methods=['POST'])
@login_required
def alterar_senha():
    nova_senha = request.form.get('nova_senha', '')
    
    if len(nova_senha) < 6:
        return "Senha deve ter pelo menos 6 caracteres.", 400
    
    user = User.query.get(session['user_id'])
    user.password = generate_password_hash(nova_senha)
    db.session.commit()
    
    return redirect(url_for('minha_conta'))


@app.route('/salvar-configuracoes-deriv', methods=['POST'])
@login_required
@subscription_required
def salvar_config_deriv():
    user = User.query.get(session['user_id'])
    
    app_id = request.form.get('app_id', '').strip()
    token = request.form.get('token', '').strip()
    
    if app_id and token:
        user.deriv_app_id = app_id
        user.deriv_token = token
        db.session.commit()
        return jsonify({"status": "success", "message": "Configurações salvas!"})
    
    return jsonify({"status": "error", "message": "Preencha todos os campos."}), 400


@app.route('/salvar-configuracoes-robo', methods=['POST'])
@login_required
@subscription_required
def salvar_config_robo():
    user = User.query.get(session['user_id'])
    
    user.valor_entrada = float(request.form.get('valor_entrada', 1.0))
    user.stop_loss = float(request.form.get('stop_loss', 10.0))
    user.take_profit = float(request.form.get('take_profit', 20.0))
    db.session.commit()
    
    return jsonify({"status": "success", "message": "Configurações do robô salvas!"})

# ==================== ROTAS DO ROBÔ (PLACEHOLDER) ====================

@app.route('/api/robot/start', methods=['POST'])
@login_required
@subscription_required
def start_robot():
    user = User.query.get(session['user_id'])
    
    if not user.deriv_app_id or not user.deriv_token:
        return jsonify({"status": "error", "message": "Configure seu Token da Deriv primeiro."}), 400
    
    user.robot_ativo = True
    db.session.commit()
    
    return jsonify({"status": "success", "message": "Robô iniciado!", "running": True})


@app.route('/api/robot/stop', methods=['POST'])
@login_required
@subscription_required
def stop_robot():
    user = User.query.get(session['user_id'])
    user.robot_ativo = False
    db.session.commit()
    
    return jsonify({"status": "success", "message": "Robô parado!", "running": False})


@app.route('/api/robot/status')
@login_required
def robot_status():
    user = User.query.get(session['user_id'])
    return jsonify({
        "running": user.robot_ativo,
        "deriv_configured": bool(user.deriv_app_id and user.deriv_token)
    })

# ==================== PAINEL ADMIN ====================

@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    users = User.query.order_by(User.criado_em.desc()).all()
    total_users = User.query.count()
    users_ativos = User.query.filter_by(status_assinatura='ativo').count()
    
    return render_template('admin.html', 
        users=users, 
        total_users=total_users,
        users_ativos=users_ativos)


@app.route('/admin/ativar/<int:user_id>')
@login_required
@admin_required
def admin_ativar_user(user_id):
    user = User.query.get(user_id)
    if user:
        user.status_assinatura = 'ativo'
        user.validade = datetime.utcnow() + timedelta(days=30)
        db.session.commit()
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/desativar/<int:user_id>')
@login_required
@admin_required
def admin_desativar_user(user_id):
    user = User.query.get(user_id)
    if user:
        user.status_assinatura = 'inativo'
        db.session.commit()
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/deletar/<int:user_id>')
@login_required
@admin_required
def admin_deletar_user(user_id):
    user = User.query.get(user_id)
    if user and user.email != Config.ADMIN_EMAIL:
        db.session.delete(user)
        db.session.commit()
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/criar-usuario', methods=['POST'])
@login_required
@admin_required
def admin_criar_user():
    email = request.form.get('email', '').lower().strip()
    senha = request.form.get('senha', 'dragon123')
    plano = request.form.get('plano', 'profissional')
    dias = int(request.form.get('dias', 30))
    
    if email and not User.query.filter_by(email=email).first():
        user = User(
            email=email,
            password=generate_password_hash(senha),
            status_assinatura='ativo',
            plano=plano,
            validade=datetime.utcnow() + timedelta(days=dias)
        )
        db.session.add(user)
        db.session.commit()
    
    return redirect(url_for('admin_dashboard'))

# ==================== WEBHOOK KIRVANO ====================

@app.route('/webhook-kirvano', methods=['POST'])
def webhook_kirvano():
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "No data"}), 400

    evento = data.get('event')
    payload = data.get('payload', {})
    email_cliente = payload.get('customer', {}).get('email', '').lower().strip()
    produto = payload.get('product', {}).get('name', '').lower()

    plano = 'profissional'
    if 'iniciante' in produto:
        plano = 'iniciante'
    elif 'elite' in produto:
        plano = 'elite'

    eventos_validos = ['order_approved', 'subscription_created', 'subscription_renewed', 'sale_approved']

    if email_cliente and evento in eventos_validos:
        user = User.query.filter_by(email=email_cliente).first()
        
        if not user:
            senha_padrao = generate_password_hash('dragon123')
            user = User(
                email=email_cliente, 
                password=senha_padrao, 
                status_assinatura='ativo',
                plano=plano,
                validade=datetime.utcnow() + timedelta(days=365)
            )
            db.session.add(user)
        else:
            user.status_assinatura = 'ativo'
            user.plano = plano
            user.validade = datetime.utcnow() + timedelta(days=365)
            
        db.session.commit()
        
        print(f"[WEBHOOK] Usuário {email_cliente} ativado - Plano: {plano}")
        
        return jsonify({"status": "success"}), 200

    return jsonify({"status": "ignored"}), 200

# ==================== ERRO HANDLER ====================

@app.errorhandler(404)
def page_not_found(e):
    return render_template('erro.html', 
        mensagem="Página não encontrada.",
        botao_texto="Voltar ao Início",
        botao_link="/"), 404

# ==================== RUN ====================

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
