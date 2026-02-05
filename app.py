import os
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# CORREÇÃO AQUI: O nome correto da chave é SQLALCHEMY_DATABASE_URI
# Usamos .get() para evitar erro caso a variável não exista localmente
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///dragonbot.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

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
    return "Página de Login do Dragon Bot - Em desenvolvimento"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
