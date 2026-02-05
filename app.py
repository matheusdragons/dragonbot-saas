from flask import Flask, render_template

app = Flask(__name__)

# Rota principal da Landing Page
@app.route('/')
def index():
    # Aqui você pode passar variáveis para o HTML, como links da Kirvano
    links_checkout = {
        "plano_basico": "https://pay.kirvano.com/seu-link-basico",
        "plano_pro": "https://pay.kirvano.com/seu-link-pro",
        "plano_vip": "https://pay.kirvano.com/seu-link-vip"
    }
    return render_template('index.html', checkouts=links_checkout)

# Rota para a área de login (exemplo)
@app.route('/login')
def login():
    # Redireciona para o sistema do robô ou página de login
    return "Página de Login do Dragon Bot - Em desenvolvimento"

if __name__ == '__main__':
    # Rodar o app em modo debug facilitar o desenvolvimento
    app.run(debug=True)
