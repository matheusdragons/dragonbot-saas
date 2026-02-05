import os
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Configuração robusta do Banco de Dados
# Se não houver DATABASE_URL, ele cria um arquivo local (sqlite) para não dar erro
database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///dragonbot.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Rota principal
@app.route('/')
def index():
    links_checkout = {
        "plano_basico": "https://pay.kirvano.com/seu-link-basico",
        "plano_pro": "https://pay.kirvano.com/seu-link-pro",
        "plano_vip": "https://pay.kirvano.com/seu-link-vip"
    }
    return render_template('index.html', checkouts=links_checkout)

@app.route('/login')
def login():
    return "Área de Login - Dragon Bot"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
