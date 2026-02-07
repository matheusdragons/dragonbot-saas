"""
DragonBot SaaS - Servidor Flask Principal
Versão: 2.0 - Integração com estratégia de Ticks
"""

import os
import asyncio
import threading
import logging
from datetime import datetime, timedelta
from functools import wraps
import uuid

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from werkzeug.security import generate_password_hash, check_password_hash

from models import db, User, Operacao, LogRobo, init_db
from bot import TradingRobot, DerivAPI

# ============================================================
# CONFIGURAÇÃO DE LOGGING
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ============================================================
# CONFIGURAÇÃO DO FLASK
# ============================================================
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dragon_secret_key_pro_99')

# Configuração do banco de dados
database_url = os.environ.get('DATABASE_URL', 'sqlite:///database.db')
# Fix para Heroku PostgreSQL
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializa o banco
init_db(app)

# ============================================================
# GERENCIADOR DE ROBÔS (em memória)
# ============================================================
class RobotManager:
    """Gerencia instâncias de robôs rodando em background."""
    
    def __init__(self):
        self.robots = {}  # user_id -> {'robot': TradingRobot, 'thread': Thread, 'loop': asyncio.loop}
        self.lock = threading.Lock()
    
    def start_robot(self, user_id, config):
        """Inicia um robô para o usuário."""
        with self.lock:
            # Para robô existente se houver
            if user_id in self.robots:
                self.stop_robot(user_id)
            
            # Cria novo robô
            robot = TradingRobot(config)
            
            # Injeta callbacks para salvar no banco
            robot.save_operation_callback = self._create_operation_callback()
            robot.save_log_callback = self._create_log_callback()
            
            # Cria thread com event loop dedicado
            loop = asyncio.new_event_loop()
            
            def run_robot():
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(robot.start())
                except Exception as e:
                    logger.error(f"Erro no robô do usuário {user_id}: {e}")
                finally:
                    loop.close()
            
            thread = threading.Thread(target=run_robot, daemon=True)
            thread.start()
            
            self.robots[user_id] = {
                'robot': robot,
                'thread': thread,
                'loop': loop,
                'started_at': datetime.now()
            }
            
            logger.info(f"✅ Robô iniciado para usuário {user_id}")
            return True
    
    def stop_robot(self, user_id):
        """Para o robô do usuário."""
        with self.lock:
            if user_id not in self.robots:
                return False
            
            robot_data = self.robots[user_id]
            robot = robot_data['robot']
            
            # Para o robô
            robot.stop()
            
            # Aguarda thread terminar (máximo 5 segundos)
            thread = robot_data['thread']
            thread.join(timeout=5)
            
            # Remove do dicionário
            del self.robots[user_id]
            
            logger.info(f"⏹️ Robô parado para usuário {user_id}")
            return True
    
    def get_status(self, user_id):
        """Retorna status do robô do usuário."""
        with self.lock:
            if user_id not in self.robots:
                return None
            
            robot = self.robots[user_id]['robot']
            return robot.get_status()
    
    def is_running(self, user_id):
        """Verifica se o robô do usuário está rodando."""
        with self.lock:
            if user_id not in self.robots:
                return False
            return self.robots[user_id]['robot'].running
    
    def _create_operation_callback(self):
        """Cria callback para salvar operações no banco."""
        def save_operation(user_id, tipo, ativo, valor, resultado, lucro, 
                          barrier=None, confianca=None, rsi=None, bollinger=None, value_chart=None):
            try:
                with app.app_context():
                    operacao = Operacao(
                        user_id=user_id,
                        tipo=tipo,
                        ativo=ativo,
                        valor=valor,
                        resultado=resultado,
                        lucro=lucro,
                        barrier=barrier,
                        confianca=confianca,
                        rsi=rsi,
                        bollinger=bollinger,
                        value_chart=value_chart,
                        data_entrada=datetime.utcnow(),
                        data_resultado=datetime.utcnow() if resultado != 'PENDING' else None
                    )
                    db.session.add(operacao)
                    db.session.commit()
                    logger.debug(f"Operação salva: {tipo} {resultado}")
            except Exception as e:
                logger.error(f"Erro ao salvar operação: {e}")
        
        return save_operation
    
    def _create_log_callback(self):
        """Cria callback para salvar logs no banco."""
        def save_log(user_id, tipo, mensagem):
            try:
                with app.app_context():
                    log = LogRobo(
                        user_id=user_id,
                        tipo=tipo,
                        mensagem=mensagem,
                        data=datetime.utcnow()
                    )
                    db.session.add(log)
                    db.session.commit()
            except Exception as e:
                logger.error(f"Erro ao salvar log: {e}")
        
        return save_log


# Instância global do gerenciador
robot_manager = RobotManager()

# ============================================================
# FUNÇÕES AUXILIARES DERIV (para testar conexão)
# ============================================================
def run_async(coro):
    """Executa coroutine em novo event loop."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def deriv_authorize(token, app_id='1089'):
    """Testa autorização com a Deriv."""
    api = DerivAPI(app_id=app_id, token=token)
    try:
        connected = await api.connect()
        if not connected:
            return None
        return api.account_info
    except Exception as e:
        logger.error(f"Erro ao autorizar Deriv: {e}")
        return None
    finally:
        await api.disconnect()


async def deriv_get_balance(token, app_id='1089'):
    """Busca saldo da conta Deriv."""
    api = DerivAPI(app_id=app_id, token=token)
    try:
        connected = await api.connect()
        if not connected:
            return None
        return await api.get_balance()
    except Exception as e:
        logger.error(f"Erro ao buscar saldo: {e}")
        return None
    finally:
        await api.disconnect()

# ============================================================
# DECORADORES DE AUTENTICAÇÃO
# ============================================================
def requer_login(f):
    """Decorator que exige usuário logado."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Faça login para continuar.', 'warning')
            return redirect(url_for('login'))
        
        # Valida session token
        user = User.query.get(session['user_id'])
        if not user or user.session_token != session.get('session_token'):
            session.clear()
            flash('Sessão expirada. Faça login novamente.', 'warning')
            return redirect(url_for('login'))
        
        return f(*args, **kwargs)
    return decorated_function


def requer_assinatura(f):
    """Decorator que exige assinatura ativa."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = User.query.get(session.get('user_id'))
        
        if not user:
            return redirect(url_for('login'))
        
        if not user.is_subscription_active():
            return redirect(url_for('assinatura_expirada'))
        
        return f(*args, **kwargs)
    return decorated_function

# ============================================================
# ROTAS PÚBLICAS
# ============================================================
@app.route('/')
def landing():
    """Landing page pública."""
    if 'user_id' in session:
        return redirect(url_for('painel'))
    return render_template('landing.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Tela e processamento de login."""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            # Gera novo token de sessão
            session_token = user.generate_session_token()
            user.ultimo_acesso = datetime.utcnow()
            db.session.commit()
            
            # Salva na sessão
            session['user_id'] = user.id
            session['session_token'] = session_token
            session['email'] = user.email
            
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('painel'))
        else:
            flash('Email ou senha incorretos.', 'danger')
    
    return render_template('login.html')


@app.route('/logout')
def logout():
    """Logout do usuário."""
    user_id = session.get('user_id')
    
    # Para o robô se estiver rodando
    if user_id and robot_manager.is_running(user_id):
        robot_manager.stop_robot(user_id)
        
        # Atualiza banco
        user = User.query.get(user_id)
        if user:
            user.robot_ativo = False
            db.session.commit()
    
    session.clear()
    flash('Você saiu do sistema.', 'info')
    return redirect(url_for('landing'))


@app.route('/assinatura-expirada')
@requer_login
def assinatura_expirada():
    """Página de assinatura expirada."""
    return render_template('erro.html', 
                          titulo='Assinatura Expirada',
                          mensagem='Sua assinatura expirou. Renove para continuar usando o DragonBot.')

# ============================================================
# ROTAS DA ÁREA DO CLIENTE
# ============================================================
@app.route('/painel')
@requer_login
@requer_assinatura
def painel():
    """Dashboard principal."""
    user = User.query.get(session['user_id'])
    
    # Busca estatísticas
    hoje = datetime.utcnow().date()
    operacoes_hoje = Operacao.query.filter(
        Operacao.user_id == user.id,
        db.func.date(Operacao.data_entrada) == hoje
    ).all()
    
    wins = sum(1 for op in operacoes_hoje if op.resultado == 'WIN')
    losses = sum(1 for op in operacoes_hoje if op.resultado == 'LOSS')
    lucro_hoje = sum(op.lucro for op in operacoes_hoje if op.lucro)
    
    # Status do robô
    robot_status = robot_manager.get_status(user.id)
    
    return render_template('painel.html', 
                          user=user,
                          operacoes_hoje=len(operacoes_hoje),
                          wins=wins,
                          losses=losses,
                          lucro_hoje=lucro_hoje,
                          robot_status=robot_status,
                          robot_running=robot_manager.is_running(user.id))


@app.route('/conta')
@requer_login
@requer_assinatura
def conta():
    """Página de configurações da conta."""
    user = User.query.get(session['user_id'])
    return render_template('conta.html', user=user)


@app.route('/operacoes')
@requer_login
@requer_assinatura
def operacoes():
    """Histórico de operações."""
    user = User.query.get(session['user_id'])
    
    # Busca últimas 100 operações
    ops = Operacao.query.filter_by(user_id=user.id)\
                        .order_by(Operacao.data_entrada.desc())\
                        .limit(100).all()
    
    return render_template('operacoes.html', user=user, operacoes=ops)


@app.route('/educacional')
@requer_login
@requer_assinatura
def educacional():
    """Área educacional."""
    user = User.query.get(session['user_id'])
    return render_template('educacional.html', user=user)

# ============================================================
# APIs DE CONFIGURAÇÃO
# ============================================================
@app.route('/api/salvar-config', methods=['POST'])
@requer_login
def api_salvar_config():
    """Salva configurações do usuário."""
    try:
        user = User.query.get(session['user_id'])
        data = request.json
        
        # Atualiza campos
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
        if 'ativo_preferido' in data:
            user.ativo_preferido = data['ativo_preferido']
        if 'deriv_token' in data:
            user.deriv_token = data['deriv_token']
        if 'deriv_app_id' in data:
            user.deriv_app_id = data['deriv_app_id']
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Configurações salvas!'})
    
    except Exception as e:
        logger.error(f"Erro ao salvar config: {e}")
        return jsonify({'success': False, 'message': str(e)}), 400


@app.route('/api/alterar-senha', methods=['POST'])
@requer_login
def api_alterar_senha():
    """Altera senha do usuário."""
    try:
        user = User.query.get(session['user_id'])
        data = request.json
        
        senha_atual = data.get('senha_atual', '')
        nova_senha = data.get('nova_senha', '')
        
        if not user.check_password(senha_atual):
            return jsonify({'success': False, 'message': 'Senha atual incorreta'}), 400
        
        if len(nova_senha) < 6:
            return jsonify({'success': False, 'message': 'Nova senha deve ter no mínimo 6 caracteres'}), 400
        
        user.set_password(nova_senha)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Senha alterada com sucesso!'})
    
    except Exception as e:
        logger.error(f"Erro ao alterar senha: {e}")
        return jsonify({'success': False, 'message': str(e)}), 400

# ============================================================
# APIs DERIV
# ============================================================
@app.route('/api/deriv/testar-conexao', methods=['POST'])
@requer_login
def api_testar_conexao():
    """Testa conexão com a Deriv."""
    try:
        user = User.query.get(session['user_id'])
        data = request.json
        
        token = data.get('token') or user.deriv_token
        app_id = data.get('app_id') or user.deriv_app_id or '1089'
        
        if not token:
            return jsonify({'success': False, 'message': 'Token não fornecido'}), 400
        
        # Testa conexão
        account_info = run_async(deriv_authorize(token, app_id))
        
        if account_info:
            # Salva token se for novo
            if data.get('token'):
                user.deriv_token = token
                user.deriv_app_id = app_id
                db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Conexão bem-sucedida!',
                'account': {
                    'email': account_info.get('email'),
                    'balance': account_info.get('balance'),
                    'currency': account_info.get('currency'),
                    'loginid': account_info.get('loginid')
                }
            })
        else:
            return jsonify({'success': False, 'message': 'Falha na autorização. Verifique o token.'}), 400
    
    except Exception as e:
        logger.error(f"Erro ao testar conexão: {e}")
        return jsonify({'success': False, 'message': str(e)}), 400


@app.route('/api/deriv/saldo')
@requer_login
def api_deriv_saldo():
    """Retorna saldo da conta Deriv."""
    try:
        user = User.query.get(session['user_id'])
        
        if not user.deriv_token:
            return jsonify({'success': False, 'message': 'Token Deriv não configurado'}), 400
        
        balance_info = run_async(deriv_get_balance(user.deriv_token, user.deriv_app_id))
        
        if balance_info:
            return jsonify({
                'success': True,
                'balance': balance_info['balance'],
                'currency': balance_info['currency']
            })
        else:
            return jsonify({'success': False, 'message': 'Não foi possível obter saldo'}), 400
    
    except Exception as e:
        logger.error(f"Erro ao buscar saldo: {e}")
        return jsonify({'success': False, 'message': str(e)}), 400

# ============================================================
# APIs DO ROBÔ
# ============================================================
@app.route('/api/robot/start', methods=['POST'])
@requer_login
@requer_assinatura
def api_robot_start():
    """Inicia o robô de trading."""
    try:
        user = User.query.get(session['user_id'])
        
        # Valida token Deriv
        if not user.deriv_token:
            return jsonify({
                'success': False, 
                'message': 'Configure seu token da Deriv antes de iniciar o robô'
            }), 400
        
        # Verifica se já está rodando
        if robot_manager.is_running(user.id):
            return jsonify({
                'success': False, 
                'message': 'Robô já está em execução'
            }), 400
        
        # Pega configurações do usuário
        config = user.get_config()
        
        # Inicia o robô
        success = robot_manager.start_robot(user.id, config)
        
        if success:
            # Atualiza status no banco
            user.robot_ativo = True
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Robô iniciado com sucesso!',
                'config': {
                    'ativo': config['ativo'],
                    'valor_entrada': config['valor_entrada'],
                    'stop_loss': config['stop_loss'],
                    'take_profit': config['take_profit']
                }
            })
        else:
            return jsonify({
                'success': False, 
                'message': 'Falha ao iniciar o robô'
            }), 500
    
    except Exception as e:
        logger.error(f"Erro ao iniciar robô: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/robot/stop', methods=['POST'])
@requer_login
def api_robot_stop():
    """Para o robô de trading."""
    try:
        user = User.query.get(session['user_id'])
        
        # Para o robô
        success = robot_manager.stop_robot(user.id)
        
        # Atualiza status no banco
        user.robot_ativo = False
        db.session.commit()
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Robô parado com sucesso!'
            })
        else:
            return jsonify({
                'success': True,
                'message': 'Robô não estava em execução'
            })
    
    except Exception as e:
        logger.error(f"Erro ao parar robô: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/robot/status')
@requer_login
def api_robot_status():
    """Retorna status atual do robô."""
    try:
        user = User.query.get(session['user_id'])
        
        # Status do gerenciador
        status = robot_manager.get_status(user.id)
        is_running = robot_manager.is_running(user.id)
        
        if status:
            return jsonify({
                'success': True,
                'running': is_running,
                'status': status
            })
        else:
            # Busca estatísticas do banco mesmo se robô não estiver rodando
            hoje = datetime.utcnow().date()
            operacoes_hoje = Operacao.query.filter(
                Operacao.user_id == user.id,
                db.func.date(Operacao.data_entrada) == hoje
            ).all()
            
            wins = sum(1 for op in operacoes_hoje if op.resultado == 'WIN')
            losses = sum(1 for op in operacoes_hoje if op.resultado == 'LOSS')
            lucro = sum(op.lucro for op in operacoes_hoje if op.lucro)
            
            return jsonify({
                'success': True,
                'running': False,
                'status': {
                    'running': False,
                    'operacoes_hoje': len(operacoes_hoje),
                    'wins': wins,
                    'losses': losses,
                    'lucro_total': lucro,
                    'logs': []
                }
            })
    
    except Exception as e:
        logger.error(f"Erro ao buscar status: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/robot/logs')
@requer_login
def api_robot_logs():
    """Retorna logs do robô."""
    try:
        user = User.query.get(session['user_id'])
        
        # Logs em tempo real (se rodando)
        status = robot_manager.get_status(user.id)
        if status and status.get('logs'):
            return jsonify({
                'success': True,
                'logs': status['logs']
            })
        
        # Logs do banco (últimos 50)
        logs = LogRobo.query.filter_by(user_id=user.id)\
                           .order_by(LogRobo.data.desc())\
                           .limit(50).all()
        
        return jsonify({
            'success': True,
            'logs': [{
                'tipo': log.tipo,
                'mensagem': log.mensagem,
                'data': log.data.isoformat()
            } for log in logs]
        })
    
    except Exception as e:
        logger.error(f"Erro ao buscar logs: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ============================================================
# WEBHOOK KIRVANO
# ============================================================
@app.route('/webhook-kirvano', methods=['POST'])
def webhook_kirvano():
    """Processa webhooks do Kirvano (pagamentos)."""
    try:
        data = request.json
        logger.info(f"Webhook Kirvano recebido: {data}")
        
        evento = data.get('event')
        email = data.get('customer', {}).get('email', '').lower()
        plano = data.get('product', {}).get('name', 'mensal').lower()
        
        if not email:
            return jsonify({'error': 'Email não fornecido'}), 400
        
        user = User.query.filter_by(email=email).first()
        
        if evento in ['purchase_approved', 'subscription_active']:
            # Ativa/renova assinatura
            if not user:
                # Cria novo usuário
                user = User(email=email)
                user.set_password(str(uuid.uuid4())[:8])  # Senha temporária
                db.session.add(user)
            
            user.status_assinatura = 'ativo'
            user.plano = 'trimestral' if 'trimestral' in plano else 'mensal'
            
            # Define validade
            dias = 90 if user.plano == 'trimestral' else 30
            user.validade = datetime.utcnow() + timedelta(days=dias)
            
            db.session.commit()
            logger.info(f"✅ Assinatura ativada para {email}")
            
        elif evento in ['subscription_canceled', 'subscription_expired', 'refund_approved']:
            # Cancela assinatura
            if user:
                user.status_assinatura = 'inativo'
                db.session.commit()
                
                # Para o robô se estiver rodando
                if robot_manager.is_running(user.id):
                    robot_manager.stop_robot(user.id)
                
                logger.info(f"❌ Assinatura cancelada para {email}")
        
        return jsonify({'success': True})
    
    except Exception as e:
        logger.error(f"Erro no webhook: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================
# ROTA DE TESTE (criar usuário de teste)
# ============================================================
@app.route('/criar-teste-dragon-2024')
def criar_usuario_teste():
    """Cria usuário de teste para desenvolvimento."""
    try:
        email = 'teste@dragonbot.com'
        
        user = User.query.filter_by(email=email).first()
        
        if not user:
            user = User(email=email)
            db.session.add(user)
        
        user.set_password('dragon123')
        user.status_assinatura = 'ativo'
        user.plano = 'mensal'
        user.validade = datetime.utcnow() + timedelta(days=30)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Usuário de teste criado/atualizado!',
            'credentials': {
                'email': email,
                'password': 'dragon123'
            }
        })
    
    except Exception as e:
        logger.error(f"Erro ao criar usuário teste: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================
# TRATAMENTO DE ERROS
# ============================================================
@app.errorhandler(404)
def page_not_found(e):
    return render_template('erro.html', 
                          titulo='Página não encontrada',
                          mensagem='A página que você procura não existe.'), 404


@app.errorhandler(500)
def internal_error(e):
    return render_template('erro.html',
                          titulo='Erro interno',
                          mensagem='Ocorreu um erro no servidor. Tente novamente.'), 500

# ============================================================
# INICIALIZAÇÃO
# ============================================================
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        logger.info("✅ Banco de dados inicializado")
    
    # Modo desenvolvimento
    app.run(debug=True, host='0.0.0.0', port=5000)
