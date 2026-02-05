import os
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Configuração do Banco de Dados (usando a URL que o Railway fornece automaticamente)
app.config['SQLALCHEMY_DATABASE_ENV'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Rota principal da Landing Page
@app.route('/')
def index():
    # Links reais da Kirvano (substitua pelos seus links de checkout)
    links_checkout = {
        "plano_basico": "https://pay.kirvano.com/seu-link-basico",
        "plano_pro": "https://pay.kirvano.com/seu-link-pro",
        "plano_vip": "https://pay.kirvano.com/seu-link-vip"
    }
    return render_template('index.html', checkouts=links_checkout)

# Rota para a área de login
@app.route('/login')
def login():
    return "Página de Login do Dragon Bot - Em desenvolvimento"

if __name__ == '__main__':
    # O Railway exige que o app rode na porta definida pela variável de ambiente PORT
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
