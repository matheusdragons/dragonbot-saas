import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import uuid
import asyncio
import json
import websockets

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
    deriv_account_type = db.Column(db.String(20), default='demo')
    
    # Configurações do Robô
    robot_ativo = db.Column(db.Boolean, default=False)
    valor_entrada = db.Column(db.Float, default=1.0)
    stop_loss = db.Column(db.Float, default=50.0)
    take_profit = db.Column(db.Float, default=100.0)
    max_operacoes_dia = db.Column(db.Integer, default=50)
    tipo_gestao = db.Column(db.String(20), default='fixo')
    nivel_martingale = db.Column(db.Float, default=2.0)
    
    # Tipo de Estratégia
    estrategia_tipo = db.Column(db.String(20), default='technical')
    
    # Controle
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    ultimo_acesso = db.Column(db.DateTime, default=datetime.utcnow)


class Operacao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    tipo = db.Column(db.String(20))
    ativo = db.Column(db.String(50), default='R_75')
    valor = db.Column(db.Float)
    resultado = db.Column(db.String(10))
    lucro = db.Column(db.Float, default=0)
    
    # Para estratégia Over/Under
    barrier = db.Column(db.String(5))
    
    rsi = db.Column(db.Float, nullable=True)
    bollinger = db.Column(db.String(20), nullable=True)
    value_chart = db.Column(db.Float, nullable=True)
    
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


# ==================== FUNÇÕES DERIV API ====================

async def deriv_authorize(token):
    """Testa conexão com a Deriv e retorna dados da conta"""
    try:
        uri = "wss://ws.binaryws.com/websockets/v3?app_id=1089"
        
        async with websockets.connect(uri) as ws:
            await ws.send(json.dumps({"authorize": token}))
            response = await asyncio.wait_for(ws.recv(), timeout=10)
            data = json.loads(response)
            
            if 'error' in data:
                return {'success': False, 'error': data['error']['message']}
            
            if 'authorize' in data:
                auth = data['authorize']
                return {
                    'success': True,
                    'email': auth.get('email', ''),
                    'fullname': auth.get('fullname', ''),
                    'balance': auth.get('balance', 0),
                    'currency': auth.get('currency', 'USD'),
                    'loginid': auth.get('loginid', ''),
                    'is_virtual': auth.get('is_virtual', 1),
                    'account_list': auth.get('account_list', [])
                }
            
            return {'success': False, 'error': 'Resposta inválida'}
            
    except asyncio.TimeoutError:
        return {'success': False, 'error': 'Timeout - Conexão demorou muito'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


async def deriv_get_balance(token):
    """Busca saldo atual da conta"""
    try:
        uri = "wss://ws.binaryws.com/websockets/v3?app_id=1089"
        
        async with websockets.connect(uri) as ws:
            await ws.send(json.dumps({"authorize": token}))
            response = await asyncio.wait_for(ws.recv(), timeout=10)
            data = json.loads(response)
            
            if 'error' in data:
                return {'success': False, 'error': data['error']['message']}
            
            await ws.send(json.dumps({"balance": 1, "subscribe": 0}))
            response = await asyncio.wait_for(ws.recv(), timeout=10)
            data = json.loads(response)
            
            if 'balance' in data:
                return {
                    'success': True,
                    'balance': data['balance']['balance'],
                    'currency': data['balance']['currency'],
                    'loginid': data['balance']['loginid']
                }
            
            return {'success': False, 'error': 'Não foi possível obter saldo'}
            
    except Exception as e:
        return {'success': False, 'error': str(e)}


def run_async(coro):
    """Helper para rodar funções async no Flask"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


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
    if 'estrategia_tipo' in data:
        user.estrategia_tipo = data['estrategia_tipo']
    
    db.session.commit()
    
    return jsonify({'status': 'success', 'message': 'Configurações salvas!'})


@app.route('/api/deriv/testar-conexao', methods=['POST'])
@requer_login
def testar_conexao_deriv():
    """Testa se o token da Deriv é válido"""
    user = usuario_logado()
    data = request.get_json()
    
    token = data.get('token', user.deriv_token)
    
    if not token:
        return jsonify({'success': False, 'error': 'Token não fornecido'})
    
    result = run_async(deriv_authorize(token))
    
    if result['success']:
        user.deriv_token = token
        db.session.commit()
        
        log = LogRobo(user_id=user.id, tipo='INFO', mensagem=f"Conectado à Deriv - Conta: {result['loginid']}")
        db.session.add(log)
        db.session.commit()
    
    return jsonify(result)


@app.route('/api/deriv/saldo')
@requer_login
def get_saldo_deriv():
    """Retorna saldo atual da conta Deriv"""
    user = usuario_logado()
    
    if not user.deriv_token:
        return jsonify({'success': False, 'error': 'Token não configurado'})
    
    result = run_async(deriv_get_balance(user.deriv_token))
    
    return jsonify(result)


@app.route('/api/deriv/contas')
@requer_login
def get_contas_deriv():
    """Lista todas as contas disponíveis (demo e real)"""
    user = usuario_logado()
    
    if not user.deriv_token:
        return jsonify({'success': False, 'error': 'Token não configurado'})
    
    result = run_async(deriv_authorize(user.deriv_token))
    
    if result['success']:
        contas = []
        for acc in result.get('account_list', []):
            contas.append({
                'loginid': acc.get('loginid', ''),
                'is_virtual': acc.get('is_virtual', 1),
                'currency': acc.get('currency', 'USD'),
                'tipo': 'Demo' if acc.get('is_virtual', 1) else 'Real'
            })
        
        return jsonify({
            'success': True,
            'conta_atual': result['loginid'],
            'is_demo': result['is_virtual'],
            'contas': contas
        })
    
    return jsonify(result)


@app.route('/api/deriv/trocar-conta', methods=['POST'])
@requer_login
def trocar_conta_deriv():
    """Troca para outra conta (demo/real)"""
    user = usuario_logado()
    data = request.get_json()
    
    tipo_desejado = data.get('tipo', 'demo')
    
    if not user.deriv_token:
        return jsonify({'success': False, 'error': 'Token não configurado'})
    
    result = run_async(deriv_authorize(user.deriv_token))
    
    if not result['success']:
        return jsonify(result)
    
    conta_encontrada = None
    for acc in result.get('account_list', []):
        is_virtual = acc.get('is_virtual', 1)
        if tipo_desejado == 'demo' and is_virtual:
            conta_encontrada = acc
            break
        elif tipo_desejado == 'real' and not is_virtual:
            conta_encontrada = acc
            break
    
    if conta_encontrada:
        user.deriv_account_type = tipo_desejado
        db.session.commit()
        
        log = LogRobo(user_id=user.id, tipo='INFO', mensagem=f"Trocou para conta {tipo_desejado.upper()}: {conta_encontrada['loginid']}")
        db.session.add(log)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f"Trocado para conta {tipo_desejado.upper()}",
            'loginid': conta_encontrada['loginid'],
            'tipo': tipo_desejado
        })
    else:
        return jsonify({
            'success': False,
            'error': f"Conta {tipo_desejado} não encontrada. Você precisa criar uma conta {tipo_desejado} na Deriv."
        })


@app.route('/api/robot/start', methods=['POST'])
@requer_login
@requer_assinatura
def robot_start():
    user = usuario_logado()
    
    if not user.deriv_token:
        return jsonify({'status': 'error', 'message': 'Configure seu Token da Deriv primeiro!'})
    
    result = run_async(deriv_authorize(user.deriv_token))
    if not result['success']:
        return jsonify({'status': 'error', 'message': f"Erro na conexão: {result['error']}"})
    
    user.robot_ativo = True
    db.session.commit()
    
    estrategia_nome = 'Probabilidade' if user.estrategia_tipo == 'probability' else 'Técnica'
    log = LogRobo(user_id=user.id, tipo='INFO', mensagem=f'Robô iniciado - Estratégia: {estrategia_nome}')
    db.session.add(log)
    db.session.commit()
    
    return jsonify({'status': 'success', 'message': 'Robô iniciado!', 'running': True})


@app.route('/api/robot/stop', methods=['POST'])
@requer_login
def robot_stop():
    user = usuario_logado()
    
    user.robot_ativo = False
    db.session.commit()
    
    log = LogRobo(user_id=user.id, tipo='INFO', mensagem='Robô parado pelo usuário')
    db.session.add(log)
    db.session.commit()
    
    return jsonify({'status': 'success', 'message': 'Robô parado!', 'running': False})


@app.route('/api/robot/status')
@requer_login
def robot_status():
    user = usuario_logado()
    
    logs = LogRobo.query.filter_by(user_id=user.id).order_by(LogRobo.data.desc()).limit(20).all()
    logs_list = [{
        'tipo': l.tipo,
        'mensagem': l.mensagem,
        'data': l.data.strftime('%H:%M:%S')
    } for l in logs]
    
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
        'operacoes_dia': ops_dia,
        'account_type': user.deriv_account_type or 'demo',
        'estrategia_tipo': user.estrategia_tipo or 'technical'
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


# ==================== ROTA TEMPORÁRIA PARA TESTE ====================

@app.route('/criar-teste-dragon-2024')
def criar_usuario_teste():
    user_existente = User.query.filter_by(email='teste@dragonbot.com').first()
    if user_existente:
        return """
        <html>
        <body style="background: #0b0e14; color: white; font-family: Arial; text-align: center; padding: 100px;">
            <h1 style="color: #00d9ff;">✅ Usuário já existe!</h1>
            <p>Email: teste@dragonbot.com</p>
            <p>Senha: dragon123</p>
            <a href="/login" style="display: inline-block; margin-top: 20px; padding: 15px 30px; background: #00ff88; color: black; text-decoration: none; border-radius: 8px; font-weight: bold;">FAZER LOGIN</a>
        </body>
        </html>
        """
    
    novo_user = User(
        email='teste@dragonbot.com',
        password=generate_password_hash('dragon123'),
        status_assinatura='ativo',
        plano='mensal',
        validade=datetime.utcnow() + timedelta(days=365),
        deriv_app_id='1089',
        robot_ativo=False,
        valor_entrada=1.0,
        stop_loss=50.0,
        take_profit=100.0,
        max_operacoes_dia=50,
        tipo_gestao='fixo',
        nivel_martingale=2.0,
        estrategia_tipo='technical'
    )
    
    db.session.add(novo_user)
    db.session.commit()
    
    return """
    <html>
    <body style="background: #0b0e14; color: white; font-family: Arial; text-align: center; padding: 100px;">
        <h1 style="color: #00ff88;">🎉 Usuário criado com sucesso!</h1>
        <div style="background: #161a23; padding: 30px; border-radius: 15px; display: inline-block; margin-top: 30px;">
            <p><strong>Email:</strong> teste@dragonbot.com</p>
            <p><strong>Senha:</strong> dragon123</p>
        </div>
        <br><br>
        <a href="/login" style="display: inline-block; padding: 15px 30px; background: #00ff88; color: black; text-decoration: none; border-radius: 8px; font-weight: bold;">FAZER LOGIN AGORA</a>
    </body>
    </html>
    """


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
