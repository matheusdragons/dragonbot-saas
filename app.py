import os
from flask import Flask, render_template

# Configuração simples e direta
app = Flask(__name__, template_folder='templates')

@app.route('/')
def index():
    # Renderiza o arquivo que você me enviou
    return render_template('index.html')

if __name__ == '__main__':
    # O Railway exige que a porta seja lida da variável de ambiente
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
