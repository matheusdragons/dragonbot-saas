import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import uuid
import asyncio
import threading

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dragon_secret_key_pro_99')

# CONFIGURAÇÃO DO BANCO
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ==================== MODELOS ====================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    
    # Assinatura
    status_assinatura = db.Column(db.String(20), default='inativo')
    plano = db.Column(db.String(50), default='mensal')
    validade = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Segurança
    session_token = db.Column(db.String(100), unique=True)
    
    # Deriv
    deriv_token = db.Column(db.String(200))
    deriv_app_id = db.Column(db.String(20), default='1089')
    
    # Configurações do Robô
    robot_ativo = db.Column(db.Boolean, default=False)
    valor_entrada = db.Column(db.Float, default=1.0)
    stop_loss = db.Column(db.Float, default=50.0)
    take_profit = db.Column(db.Float, default=100.0)
    max_operacoes_dia = db.Column(db.Integer, default=50)
    tipo_gestao = db.Column(db.String(20), default='fixo')
    nivel_martingale = db.Column(db.Float, default=2.0)
    
    # Controle
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    ultimo_acesso = db.Column(db.DateTime, default=datetime.utcnow)


class Operacao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    tipo = db.Column(db.String(10))
    ativo = db.Column(db.String(50), default='R_75')
    valor = db.Column(db.Float)
    resultado = db.Column(db.String(10))
    lucro = db.Column(db.Float, default=0)
    
    rsi = db.Column(db.Float)
    bollinger = db.Column(db.String(20))
    value_chart = db.Column(db.Float)
    
    data_entrada = db.Column(db.DateTime, default=datetime.utcnow)
    data_resultado = db.Column(db.DateTime)


class LogRobo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    tipo = db.Column(db.String(20))
    mensagem = db.Column(db.Text)
    data = db.Column(db.DateTime, default=datetime.utcnow)


with app.app_context():
    db.create_all()


# ==================== ARMAZENAMENTO DE ROBÔS ATIVOS ====================

robots_ativos = {}  # {user_id: robot_instance}


# ==================== FUNÇÕES AUXILIARES ====================

def usuario_logado():
    if 'user_id' not in session:
        return None
    user = User.query.get(session['user_id'])
    if user and session.get('session_token') == user.session_token:
        return user
    return None


def requer_login(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        user = usuario_logado()
        if not user:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def requer_assinatura(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        user = usuario_logado()
        if not user:
            return redirect(url_for('login'))
        if user.status_assinatura != 'ativo' or user.validade < datetime.utcnow():
            return redirect(url_for('assinatura_expirada'))
        return f(*args, **kwargs)
    return decorated


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
            return redirect(url_for('painel'))
        
        return render_template('login.html', erro="E-mail ou senha inválidos. Verifique seus dados e tente novamente.")
    
    return render_template('login.html')


@app.route('/logout')
def logout():
    user_id = session.get('user_id')
    if user_id and user_id in robots_ativos:
        robots_ativos[user_id].stop()
        del robots_ativos[user_id]
    session.clear()
    return redirect(url_for('landing'))


@app.route('/assinatura-expirada')
def assinatura_expirada():
    return render_template('erro.html', 
        mensagem="Sua assinatura expirou ou está inativa.",
        botao_texto="Ver Planos",
        botao_link="/#planos")


# ==================== ROTAS DO PAINEL ====================

@app.route('/painel')
@requer_login
@requer_assinatura
def painel():
    user = usuario_logado()
    return render_template('painel.html', user=user)


@app.route('/conta')
@requer_login
def conta():
    user = usuario_logado()
    return render_template('conta.html', user=user)


@app.route('/operacoes')
@requer_login
@requer_assinatura
def operacoes():
    user = usuario_logado()
    ops = Operacao.query.filter_by(user_id=user.id).order_by(Operacao.data_entrada.desc()).limit(100).all()
    
    # Cálculos
    total_ops = len(ops)
    wins = len([o for o in ops if o.resultado == 'WIN'])
    losses = len([o for o in ops if o.resultado == 'LOSS'])
    lucro_total = sum([o.lucro for o in ops if o.lucro])
    
    return render_template('operacoes.html', 
        user=user, 
        operacoes=ops,
        total_ops=total_ops,
        wins=wins,
        losses=losses,
        lucro_total=lucro_total)


@app.route('/educacional')
@requer_login
def educacional():
    user = usuario_logado()
    return render_template('educacional.html', user=user)


# ==================== API DO ROBÔ ====================

@app.route('/api/salvar-config', methods=['POST'])
@requer_login
def salvar_config():
    user = usuario_logado()
    data = request.get_json()
    
    if 'deriv_token' in data:
        user.deriv_token = data['deriv_token']
    if 'valor_entrada' in data:
        user.valor_entrada = float(data['valor_entrada'])
    if 'stop_loss' in data:
        user.stop_loss = float(data['stop_loss'])
    if 'take_profit' in data:
        user.take_profit = float(data['take_profit'])
    if 'max_operacoes_dia' in data:
        user.max_operacoes_dia = int(data['max_operacoes_dia'])
    if 'tipo_gestao' in data:
        user.tipo_gestao = data['tipo_gestao']
    if 'nivel_martingale' in data:
        user.nivel_martingale = float(data['nivel_martingale'])
    
    db.session.commit()
    
    return jsonify({'status': 'success', 'message': 'Configurações salvas!'})


@app.route('/api/robot/start', methods=['POST'])
@requer_login
@requer_assinatura
def robot_start():
    user = usuario_logado()
    
    if not user.deriv_token:
        return jsonify({'status': 'error', 'message': 'Configure seu Token da Deriv primeiro!'})
    
    user.robot_ativo = True
    db.session.commit()
    
    # Adiciona log
    log = LogRobo(user_id=user.id, tipo='INFO', mensagem='Robô iniciado pelo usuário')
    db.session.add(log)
    db.session.commit()
    
    return jsonify({'status': 'success', 'message': 'Robô iniciado!', 'running': True})


@app.route('/api/robot/stop', methods=['POST'])
@requer_login
def robot_stop():
    user = usuario_logado()
    
    user.robot_ativo = False
    db.session.commit()
    
    # Adiciona log
    log = LogRobo(user_id=user.id, tipo='INFO', mensagem='Robô parado pelo usuário')
    db.session.add(log)
    db.session.commit()
    
    return jsonify({'status': 'success', 'message': 'Robô parado!', 'running': False})


@app.route('/api/robot/status')
@requer_login
def robot_status():
    user = usuario_logado()
    
    # Busca logs recentes
    logs = LogRobo.query.filter_by(user_id=user.id).order_by(LogRobo.data.desc()).limit(20).all()
    logs_list = [{
        'tipo': l.tipo,
        'mensagem': l.mensagem,
        'data': l.data.strftime('%H:%M:%S')
    } for l in logs]
    
    # Busca operações do dia
    hoje = datetime.utcnow().date()
    ops_hoje = Operacao.query.filter(
        Operacao.user_id == user.id,
        Operacao.data_entrada >= datetime.combine(hoje, datetime.min.time())
    ).all()
    
    lucro_dia = sum([o.lucro for o in ops_hoje if o.lucro])
    ops_dia = len(ops_hoje)
    
    return jsonify({
        'running': user.robot_ativo,
        'deriv_configured': bool(user.deriv_token),
        'logs': logs_list,
        'lucro_dia': lucro_dia,
        'operacoes_dia': ops_dia
    })


@app.route('/api/alterar-senha', methods=['POST'])
@requer_login
def alterar_senha():
    user = usuario_logado()
    data = request.get_json()
    
    nova_senha = data.get('nova_senha', '')
    
    if len(nova_senha) < 6:
        return jsonify({'status': 'error', 'message': 'Senha deve ter no mínimo 6 caracteres'})
    
    user.password = generate_password_hash(nova_senha)
    db.session.commit()
    
    return jsonify({'status': 'success', 'message': 'Senha alterada com sucesso!'})


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

    # Identifica o plano
    plano = 'mensal'
    dias = 30
    if 'trimestral' in produto:
        plano = 'trimestral'
        dias = 90

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
                validade=datetime.utcnow() + timedelta(days=dias)
            )
            db.session.add(user)
        else:
            user.status_assinatura = 'ativo'
            user.plano = plano
            user.validade = datetime.utcnow() + timedelta(days=dias)
            
        db.session.commit()
        return jsonify({"status": "success"}), 200

    return jsonify({"status": "ignored"}), 200


# ==================== ERRO 404 ====================

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
