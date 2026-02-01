import sqlite3
import os
from flask import Flask, request, render_template, render_template_string

# Configuramos o Flask para encontrar a pasta 'templates' corretamente no servidor
app = Flask(__name__, template_folder='templates')

# Função para garantir que o banco de dados exista ao iniciar
def init_db():
    conn = sqlite3.connect('vendas.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS vendas 
        (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, email TEXT, status TEXT, valor TEXT, data_hora TEXT)''')
    conn.commit()
    conn.close()

# --- DASHBOARD ADMIN ---
HTML_ADMIN = '''
<body style="background:#0f172a; color:white; font-family:sans-serif; padding:40px;">
    <h1 style="color:#0ea5e9;">🐉 DragonBot SaaS - Painel Administrativo</h1>
    <p>Status do Servidor: <span style="color:#22c55e;">● Ativo na Nuvem</span></p>
    <table border="1" style="width:100%; border-collapse:collapse; background:#1e293b; border-color:#334155;">
        <tr style="background:#0ea5e9;"><th>Data</th><th>Cliente</th><th>Email</th><th>Status</th></tr>
        {% for v in vendas %}
        <tr><td>{{v[5]}}</td><td>{{v[1]}}</td><td>{{v[2]}}</td><td>{{v[3]}}</td></tr>
        {% endfor %}
    </table>
    <br>
    <div style="background:#1e293b; padding:20px; border-radius:8px;">
        <p>Link de acesso para seus clientes:</p>
        <code style="background:#000; padding:10px; color:#38bdf8; display:block;">/acesso-liberado</code>
    </div>
</body>
'''

@app.route('/')
def admin():
    conn = sqlite3.connect('vendas.db')
    c = conn.cursor()
    c.execute('SELECT * FROM vendas ORDER BY id DESC')
    v = c.fetchall()
    conn.close()
    return render_template_string(HTML_ADMIN, vendas=v)

@app.route('/acesso-liberado')
def area_cliente():
    # Renderiza o index.html que está na pasta templates
    return render_template('index.html')

@app.route('/webhook-kirvano', methods=['POST'])
def webhook():
    d = request.get_json()
    if d:
        cli = d.get('customer', {})
        conn = sqlite3.connect('vendas.db')
        c = conn.cursor()
        c.execute('INSERT INTO vendas (nome, email, status, valor, data_hora) VALUES (?, ?, ?, ?, ?)',
                  (cli.get('name'), cli.get('email'), d.get('status'), d.get('total_price'), d.get('created_at')))
        conn.commit()
        conn.close()
        print(f"💰 Venda confirmada: {cli.get('name')}")
    return "OK", 200

if __name__ == '__main__':
    init_db()
    # Pega a porta do servidor (Railway/Render) ou usa 5000 se for local
    porta = int(os.environ.get("PORT", 5000))
    # Host 0.0.0.0 é obrigatório para o servidor ser acessado externamente
    app.run(host='0.0.0.0', port=porta)