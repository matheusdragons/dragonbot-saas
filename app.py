from flask import Flask, render_template, request, jsonify # Adicione jsonify
# ... mantenha suas outras importações e configurações do Banco de Dados ...

# ROTA DO WEBHOOK: Onde a Kirvano vai enviar os avisos
@app.route('/webhook-kirvano', methods=['POST'])
def webhook_kirvano():
    data = request.get_json()
    
    # A Kirvano envia o evento e os dados do cliente
    evento = data.get('event') # Ex: 'subscription_created' ou 'order_approved'
    payload = data.get('payload', {})
    email_cliente = payload.get('customer', {}).get('email')

    if not email_cliente:
        return jsonify({"status": "erro", "message": "Email nao encontrado"}), 400

    user = User.query.filter_by(email=email_cliente).first()

    # 1. Se o pagamento foi aprovado ou assinatura criada
    if evento in ['order_approved', 'subscription_created', 'subscription_renewed']:
        if user:
            user.status_assinatura = 'ativo'
            user.validade = datetime.utcnow() + timedelta(days=30)
            db.session.commit()
            print(f"ACESSO LIBERADO: {email_cliente}")
        else:
            # Se o usuário pagou mas ainda não criou a conta no seu site
            # O sistema pode pré-autorizar o e-mail aqui se desejar
            print(f"PAGAMENTO RECEBIDO: {email_cliente} (Aguardando cadastro)")

    # 2. Se a assinatura foi cancelada ou o pagamento falhou
    elif evento in ['subscription_canceled', 'subscription_expired', 'payment_failed']:
        if user:
            user.status_assinatura = 'inativo'
            db.session.commit()
            print(f"ACESSO BLOQUEADO: {email_cliente}")

    return jsonify({"status": "sucesso"}), 200
