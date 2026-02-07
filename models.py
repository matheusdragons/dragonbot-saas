"""
DragonBot SaaS - Modelos do Banco de Dados
Versão: 2.0 - Suporte a contratos DIGIT
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import uuid

db = SQLAlchemy()


class User(db.Model):
    """Modelo de usuário do sistema."""
    
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    
    # Assinatura
    status_assinatura = db.Column(db.String(20), default='inativo')
    plano = db.Column(db.String(20), default='mensal')
    validade = db.Column(db.DateTime, nullable=True)
    
    # Segurança
    session_token = db.Column(db.String(100), nullable=True)
    
    # Deriv
    deriv_token = db.Column(db.String(255), nullable=True)
    deriv_app_id = db.Column(db.String(20), default='1089')
    deriv_account_type = db.Column(db.String(10), default='demo')
    
    # Configurações do Robô
    robot_ativo = db.Column(db.Boolean, default=False)
    valor_entrada = db.Column(db.Float, default=1.0)
    stop_loss = db.Column(db.Float, default=50.0)
    take_profit = db.Column(db.Float, default=100.0)
    max_operacoes_dia = db.Column(db.Integer, default=50)
    tipo_gestao = db.Column(db.String(20), default='fixo')
    nivel_martingale = db.Column(db.Float, default=2.0)
    ativo_preferido = db.Column(db.String(20), default='R_75')
    
    # Controle
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    ultimo_acesso = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    operacoes = db.relationship('Operacao', backref='user', lazy='dynamic')
    logs = db.relationship('LogRobo', backref='user', lazy='dynamic')
    
    def set_password(self, password):
        """Define senha com hash."""
        self.password = generate_password_hash(password)
    
    def check_password(self, password):
        """Verifica senha."""
        return check_password_hash(self.password, password)
    
    def generate_session_token(self):
        """Gera novo token de sessão."""
        self.session_token = str(uuid.uuid4())
        return self.session_token
    
    def is_subscription_active(self):
        """Verifica se assinatura está ativa."""
        if self.status_assinatura != 'ativo':
            return False
        if self.validade and self.validade < datetime.utcnow():
            return False
        return True
    
    def get_config(self):
        """Retorna configurações para o robô."""
        return {
            'user_id': self.id,
            'deriv_token': self.deriv_token,
            'deriv_app_id': self.deriv_app_id,
            'valor_entrada': self.valor_entrada,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'max_operacoes_dia': self.max_operacoes_dia,
            'tipo_gestao': self.tipo_gestao,
            'nivel_martingale': self.nivel_martingale,
            'ativo': self.ativo_preferido
        }
    
    def __repr__(self):
        return f'<User {self.email}>'


class Operacao(db.Model):
    """Modelo de operação/trade."""
    
    __tablename__ = 'operacoes'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Dados da operação
    tipo = db.Column(db.String(20), nullable=False)
    ativo = db.Column(db.String(20), default='R_75')
    valor = db.Column(db.Float, nullable=False)
    
    # Resultado
    resultado = db.Column(db.String(10), default='PENDING')
    lucro = db.Column(db.Float, default=0.0)
    
    # Para contratos DIGIT
    barrier = db.Column(db.String(5), nullable=True)
    confianca = db.Column(db.Float, nullable=True)
    
    # Indicadores técnicos (opcionais)
    rsi = db.Column(db.Float, nullable=True)
    bollinger = db.Column(db.String(20), nullable=True)
    value_chart = db.Column(db.Float, nullable=True)
    
    # Timestamps
    data_entrada = db.Column(db.DateTime, default=datetime.utcnow)
    data_resultado = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f'<Operacao {self.id} {self.tipo} {self.resultado}>'


class LogRobo(db.Model):
    """Modelo de log do robô."""
    
    __tablename__ = 'logs_robo'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    tipo = db.Column(db.String(20), nullable=False)
    mensagem = db.Column(db.Text, nullable=False)
    data = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<LogRobo {self.id} {self.tipo}>'


def init_db(app):
    """Inicializa o banco de dados."""
    db.init_app(app)
    with app.app_context():
        db.create_all()
