from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# ==================== USUÁRIO ====================
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
    
    # Gestão de Banca
    tipo_gestao = db.Column(db.String(20), default='fixo')
    nivel_martingale = db.Column(db.Float, default=2.0)
    
    # NOVO: Tipo de Estratégia
    estrategia_tipo = db.Column(db.String(20), default='technical')
    
    # Controle
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    ultimo_acesso = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    operacoes = db.relationship('Operacao', backref='user', lazy=True)


# ==================== OPERAÇÕES ====================
class Operacao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Dados da operação
    tipo = db.Column(db.String(20))
    ativo = db.Column(db.String(50), default='R_75')
    valor = db.Column(db.Float)
    
    # NOVO: Para estratégia Over/Under
    barrier = db.Column(db.String(5))
    
    # Resultado
    resultado = db.Column(db.String(10))
    lucro = db.Column(db.Float, default=0)
    
    # Indicadores no momento da entrada (opcionais)
    rsi = db.Column(db.Float, nullable=True)
    bollinger = db.Column(db.String(20), nullable=True)
    value_chart = db.Column(db.Float, nullable=True)
    
    # Timestamps
    data_entrada = db.Column(db.DateTime, default=datetime.utcnow)
    data_resultado = db.Column(db.DateTime)


# ==================== LOGS DO ROBÔ ====================
class LogRobo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    tipo = db.Column(db.String(20))
    mensagem = db.Column(db.Text)
    data = db.Column(db.DateTime, default=datetime.utcnow)
