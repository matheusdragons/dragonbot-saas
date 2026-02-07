"""
DragonBot SaaS - Servidor Flask Principal
Versão: 6.0 - Correção do travamento
"""

import os
import sys
import asyncio
import threading
import logging
from datetime import datetime, timedelta
from functools import wraps
import uuid
import json

# Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Flask
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from werkzeug.security import generate_password_hash, check_password_hash

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Flask App
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dragon_secret_key_pro_99')

# Database
database_url = os.environ.get('DATABASE_URL', 'sqlite:///database.db')
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Import models
from models import db, User, Operacao, LogRobo, init_db
init_db(app)

# Import bot - com tratamento de erro
BOT_AVAILABLE = False
try:
    from bot.robot import TradingRobot
    from bot.deriv_api import DerivAPI
    BOT_AVAILABLE = True
    logger.info("✅ Módulo bot carregado")
except ImportError as e:
    logger.warning(f"⚠️ Bot não disponível: {e}")

# ============================================================
# ROBOT MANAGER SIMPLIFICADO
# ============================================================
class SimpleRobotManager:
    def __init__(self):
        self.robots = {}
        self.enabled = BOT_AVAILABLE
        logger.info(f"🤖 Robot Manager iniciado - Bot disponível: {self.enabled}")
    
    def start_robot(self, user_id, config):
        """Inicia robô em thread separada."""
        if not self.enabled:
            logger.error("Bot não está disponível")
            return False
        
        try:
            # Para robô anterior se existir
            if user_id in self.robots:
                self.stop_robot(user_id)
            
            logger.info(f"🚀 Iniciando robô para usuário {user_id}...")
            
            # Cria o robô
            robot = TradingRobot(config)
            
            # Callbacks para salvar no banco
            def save_operation(user_id, tipo, ativo, valor, resultado, lucro, barrier=None, confianca=None, **kwargs):
                try:
                    with app.app_context():
                        op = Operacao(
                            user_id=user_id,
                            tipo=tipo,
                            ativo=ativo,
                            valor=valor,
                            resultado=resultado,
                            lucro=lucro,
                            barrier=barrier,
                            confianca=confianca,
                            data_entrada=datetime.utcnow()
                        )
                        db.session.add(op)
                        db.session.commit()
                        logger.debug(f"Operação salva: {tipo} {resultado}")
                except Exception as e:
                    logger.error(f"Erro ao salvar operação: {e}")
            
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
            
            robot.save_operation_callback = save_operation
            robot.save_log_callback = save_log
            
            # Função que roda em thread
            def run_robot_thread():
                logger.info(f"🏃 Thread do robô iniciada para usuário {user_id}")
                
                # Cria novo event loop para esta thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    # Roda o robô
                    loop.run_until_complete(robot.start())
                except Exception as e:
                    logger.error(f"❌ Erro no robô: {e}")
                finally:
                    loop.close()
                    logger.info(f"🛑 Thread do robô finalizada para usuário {user_id}")
            
            # Cria e inicia a thread
            thread = threading.Thread(target=run_robot_thread, daemon=True)
            thread.start()
            
            # Salva referências
            self.robots[user_id] = {
                'robot': robot,
                'thread': thread,
                'started_at': datetime.now()
            }
            
            logger.info(f"✅ Robô iniciado com sucesso para usuário {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao iniciar robô: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def stop_robot(self, user_id):
        """Para o robô do usuário."""
        if user_id not in self.robots:
            logger.info(f"Robô não encontrado para usuário {user_id}")
            return False
        
        try:
            robot_data = self.robots[user_id]
            robot = robot_data['robot']
            
            # Para o robô
            robot.stop()
            
            # Remove da lista
            del self.robots[user_id]
            
            logger.info(f"✅ Robô parado para usuário {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao parar robô: {e}")
            return False
    
    def get_status(self, user_id):
        """Retorna status do robô."""
        if user_id not in self.robots:
            return None
        
        try:
            robot = self.robots[user_id]['robot']
            return robot.get_status()
        except:
            return None
    
    def is_running(self, user_id):
        """Verifica se robô está rodando."""
        return user_id in self.robots


# Instância global
robot_manager = SimpleRobotManager()

# ============================================================
# HELPERS
# ============================================================
def run_async(coro):
    """Executa coroutine."""
    if not BOT_AVAILABLE:
        return None
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(coro)
        loop.close()
        return result
    except Exception as e:
        logger.error(f"Erro run_async: {e}")
        return None

# ============================================================
# DECORATORS
# ============================================================
def requer_login(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Faça login para continuar.', 'warning')
            return redirect(url_for('login'))
        
        user = User.query.get(session['user_id'])
        if not user or user.session_token != session.get('session_token'):
            session.clear()
            flash('Sessão expirada.', 'warning')
            return redirect(url_for('login'))
        
        return f(*args, **kwargs)
    return decorated_function


def requer_assinatura(f):
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
    if 'user_id' in session:
        return redirect(url_for('painel'))
    return render_template('landing.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            session_token = user.generate_session_token()
            user.ultimo_acesso = datetime.utcnow()
            db.session.commit()
            
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
    user_id = session.get('user_id')
    
    if user_id and robot_manager.is_running(user_id):
        robot_manager.stop_robot(user_id)
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
    return render_template('erro.html', 
                          titulo='Assinatura Expirada',
                          mensagem='Renove sua assinatura para continuar.')

# ============================================================
# ÁREA DO CLIENTE
# ============================================================
@app.route('/painel')
@requer_login
@requer_assinatura
def painel():
    user = User.query.get(session['user_id'])
    
    hoje = datetime.utcnow().date()
    operacoes_hoje = Operacao.query.filter(
        Operacao.user_id == user.id,
        db.func.date(Operacao.data_entrada) == hoje
    ).all()
    
    wins = sum(1 for op in operacoes_hoje if op.resultado == 'WIN')
    losses = sum(1 for op in operacoes_hoje if op.resultado == 'LOSS')
    lucro_hoje = sum(op.lucro for op in operacoes_hoje if op.lucro)
    
    robot_status = robot_manager.get_status(user.id) if BOT_AVAILABLE else None
    
    return render_template('painel.html', 
                          user=user,
                          operacoes_hoje=len(operacoes_hoje),
                          wins=wins,
                          losses=losses,
                          lucro_hoje=lucro_hoje,
                          robot_status=robot_status,
                          robot_running=robot_manager.is_running(user.id),
                          bot_available=BOT_AVAILABLE)


@app.route('/conta')
@requer_login
@requer_assinatura
def conta():
    user = User.query.get(session['user_id'])
    return render_template('conta.html', user=user, bot_available=BOT_AVAILABLE)


@app.route('/operacoes')
@requer_login
@requer_assinatura
def operacoes():
    user = User.query.get(session['user_id'])
    ops = Operacao.query.filter_by(user_id=user.id)\
                        .order_by(Operacao.data_entrada.desc())\
                        .limit(100).all()
    return render_template('operacoes.html', user=user, operacoes=ops)


@app.route('/educacional')
@requer_login
@requer_assinatura
def educacional():
    user = User.query.get(session['user_id'])
    return render_template('educacional.html', user=user)

# ============================================================
# API DO ROBÔ - CORRIGIDA
# ============================================================
@app.route('/api/robot/start', methods=['POST'])
@requer_login
@requer_assinatura
def api_robot_start():
    """Inicia o robô - VERSÃO CORRIGIDA."""
    
    logger.info("="*60)
    logger.info("🎯 REQUISIÇÃO PARA INICIAR ROBÔ")
    logger.info("="*60)
    
    # Verifica se bot está disponível
    if not BOT_AVAILABLE:
        logger.error("Bot não está disponível")
        return jsonify({
            'success': False, 
            'message': 'Módulo do bot não está disponível'
        }), 503
    
    try:
        user = User.query.get(session['user_id'])
        
        logger.info(f"Usuário: {user.email}")
        logger.info(f"Token Deriv: {'Sim' if user.deriv_token else 'Não'}")
        
        # Valida token
        if not user.deriv_token:
            return jsonify({
                'success': False,
                'message': 'Configure seu token da Deriv antes de iniciar'
            }), 400
        
        # Verifica se já está rodando
        if robot_manager.is_running(user.id):
            return jsonify({
                'success': False,
                'message': 'Robô já está em execução'
            }), 400
        
        # Prepara configuração
        config = {
            'user_id': user.id,
            'deriv_token': user.deriv_token,
            'deriv_app_id': user.deriv_app_id or '1089',
            'valor_entrada': user.valor_entrada or 1.0,
            'stop_loss': user.stop_loss or 50.0,
            'take_profit': user.take_profit or 100.0,
            'max_operacoes_dia': user.max_operacoes_dia or 20,
            'tipo_gestao': user.tipo_gestao or 'fixo',
            'nivel_martingale': user.nivel_martingale or 2.0,
            'ativo': user.ativo_preferido or 'R_10'
        }
        
        logger.info(f"Config: {json.dumps(config, indent=2)}")
        
        # Inicia o robô
        logger.info("Chamando robot_manager.start_robot()...")
        success = robot_manager.start_robot(user.id, config)
        
        if success:
            # Atualiza status no banco
            user.robot_ativo = True
            db.session.commit()
            
            logger.info("✅ Robô iniciado com sucesso!")
            
            return jsonify({
                'success': True,
                'message': 'Robô iniciado com sucesso!',
                'status': 'running'
            })
        else:
            logger.error("Falha ao iniciar robô")
            return jsonify({
                'success': False,
                'message': 'Falha ao iniciar o robô'
            }), 500
            
    except Exception as e:
        logger.error(f"❌ ERRO: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': f'Erro: {str(e)}'
        }), 500


@app.route('/api/robot/stop', methods=['POST'])
@requer_login
def api_robot_stop():
    """Para o robô."""
    try:
        user = User.query.get(session['user_id'])
        
        success = robot_manager.stop_robot(user.id) if BOT_AVAILABLE else False
        
        user.robot_ativo = False
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Robô parado!' if success else 'Robô não estava rodando'
        })
        
    except Exception as e:
        logger.error(f"Erro ao parar robô: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/robot/status')
@requer_login
def api_robot_status():
    """Retorna status do robô."""
    try:
        user = User.query.get(session['user_id'])
        
        if not BOT_AVAILABLE:
            return jsonify({
                'success': False,
                'message': 'Bot não disponível'
            })
        
        status = robot_manager.get_status(user.id)
        is_running = robot_manager.is_running(user.id)
        
        if status:
            return jsonify({
                'success': True,
                'running': is_running,
                'status': status
            })
        else:
            # Retorna estatísticas do banco
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
        
        # Tenta pegar logs em tempo real
        if BOT_AVAILABLE:
            status = robot_manager.get_status(user.id)
            if status and status.get('logs'):
                return jsonify({
                    'success': True,
                    'logs': status['logs']
                })
        
        # Pega logs do banco
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
# CONFIGURAÇÕES
# ============================================================
@app.route('/api/salvar-config', methods=['POST'])
@requer_login
def api_salvar_config():
    try:
        user = User.query.get(session['user_id'])
        data = request.json
        
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
        if 'deriv_token' in data:
            user.deriv_token = data['deriv_token']
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Configurações salvas!'})
        
    except Exception as e:
        logger.error(f"Erro ao salvar config: {e}")
        return jsonify({'success': False, 'message': str(e)}), 400

# ============================================================
# TESTE
# ============================================================
@app.route('/criar-teste-dragon-2024')
def criar_usuario_teste():
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
            'message': 'Usuário teste criado!',
            'credentials': {
                'email': email,
                'password': 'dragon123'
            },
            'bot_available': BOT_AVAILABLE
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'bot_available': BOT_AVAILABLE,
        'timestamp': datetime.now().isoformat()
    })


@app.errorhandler(404)
def page_not_found(e):
    return render_template('erro.html', 
                          titulo='Página não encontrada',
                          mensagem='A página solicitada não existe.'), 404


@app.errorhandler(500)
def internal_error(e):
    return render_template('erro.html',
                          titulo='Erro interno',
                          mensagem='Ocorreu um erro. Tente novamente.'), 500

# ============================================================
# MAIN
# ============================================================
if __name__ == '__main__':
    with app.app_context():
        try:
            db.create_all()
            logger.info("✅ Banco de dados inicializado")
        except Exception as e:
            logger.error(f"Erro ao criar banco: {e}")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
