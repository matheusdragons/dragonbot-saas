@app.route('/webhook-kirvano', methods=['POST'])
def webhook_kirvano():
    data = request.get_json()
    evento = data.get('event')
    payload = data.get('payload', {})
    email_cliente = payload.get('customer', {}).get('email')

    if evento in ['order_approved', 'subscription_created']:
        user = User.query.filter_by(email=email_cliente).first()
        
        if not user:
            # CRIAR CONTA AUTOMÁTICA
            # Definimos uma senha padrão (ex: 'dragon123') que ele mudará no painel
            senha_padrao = generate_password_hash('dragon123')
            novo_usuario = User(
                email=email_cliente, 
                password=senha_padrao, 
                status_assinatura='ativo', 
                validade=datetime.utcnow() + timedelta(days=30)
            )
            db.session.add(novo_usuario)
            db.session.commit()
            print(f"CONTA CRIADA AUTOMATICAMENTE: {email_cliente}")
        else:
            # Se já existe, apenas renova a validade
            user.status_assinatura = 'ativo'
            user.validade = datetime.utcnow() + timedelta(days=30)
            db.session.commit()
            
    return jsonify({"status": "sucesso"}), 200
