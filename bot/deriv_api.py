"""
DragonBot SaaS - API Deriv Simplificada
Foco em DIGITDIFF para o dígito 7
"""

import json
import asyncio
import websockets
import logging

logger = logging.getLogger(__name__)


class DerivAPI:
    def __init__(self, app_id='1089', token=None):
        self.app_id = app_id
        self.token = token
        self.ws = None
        self.connected = False
        self.authorized = False
        self.account_info = None
        self.base_url = f"wss://ws.binaryws.com/websockets/v3?app_id={app_id}"
        self.req_id = 0
    
    def _next_req_id(self):
        self.req_id += 1
        return self.req_id
    
    async def connect(self):
        """Conecta ao WebSocket da Deriv."""
        try:
            logger.info("🔌 Conectando à Deriv...")
            self.ws = await websockets.connect(
                self.base_url,
                ping_interval=30,
                ping_timeout=10
            )
            self.connected = True
            logger.info("✅ Conectado!")
            
            # Se tem token, autoriza
            if self.token:
                await self.authorize()
            
            return True
        except Exception as e:
            logger.error(f"❌ Erro na conexão: {e}")
            return False
    
    async def authorize(self):
        """Autoriza com o token."""
        try:
            request = {
                "authorize": self.token,
                "req_id": self._next_req_id()
            }
            
            logger.info("🔐 Autorizando...")
            await self.ws.send(json.dumps(request))
            response = await self.ws.recv()
            data = json.loads(response)
            
            if 'error' in data:
                logger.error(f"❌ Erro: {data['error']['message']}")
                return False
            
            if 'authorize' in data:
                self.authorized = True
                self.account_info = data['authorize']
                logger.info(f"✅ Autorizado!")
                logger.info(f"💰 Saldo: {self.account_info.get('balance')} {self.account_info.get('currency')}")
                return True
            
            return False
        except Exception as e:
            logger.error(f"❌ Erro na autorização: {e}")
            return False
    
    async def get_balance(self):
        """Retorna o saldo atual."""
        try:
            request = {
                "balance": 1,
                "subscribe": 0,
                "req_id": self._next_req_id()
            }
            
            await self.ws.send(json.dumps(request))
            response = await self.ws.recv()
            data = json.loads(response)
            
            if 'balance' in data:
                return {
                    'balance': float(data['balance']['balance']),
                    'currency': data['balance']['currency']
                }
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar saldo: {e}")
            return None
    
    async def get_ticks(self, symbol="R_10", count=10):
        """Busca os últimos ticks."""
        try:
            request = {
                "ticks_history": symbol,
                "style": "ticks",
                "end": "latest",
                "count": count,
                "req_id": self._next_req_id()
            }
            
            logger.info(f"📈 Buscando {count} ticks de {symbol}...")
            await self.ws.send(json.dumps(request))
            response = await self.ws.recv()
            data = json.loads(response)
            
            if 'error' in data:
                logger.error(f"Erro: {data['error']['message']}")
                return None
            
            if 'history' in data:
                prices = data['history'].get('prices', [])
                ticks = []
                for price in prices:
                    ticks.append({'quote': float(price)})
                
                if ticks:
                    logger.info(f"✅ {len(ticks)} ticks recebidos")
                    logger.info(f"   Último preço: {ticks[-1]['quote']}")
                
                return ticks
            
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar ticks: {e}")
            return None
    
    async def buy_digitdiff(self, amount=1.0, barrier=7, symbol="R_10"):
        """
        Compra contrato DIGITDIFF específico para o dígito 7.
        DIGITDIFF = Ganha se o próximo tick NÃO terminar em 7
        """
        try:
            logger.info("="*50)
            logger.info("🎯 COMPRANDO DIGITDIFF")
            logger.info(f"   Barrier: {barrier}")
            logger.info(f"   Valor: ${amount}")
            logger.info(f"   Ativo: {symbol}")
            logger.info("="*50)
            
            # Primeiro, solicita proposta
            proposal_request = {
                "proposal": 1,
                "amount": float(amount),
                "basis": "stake",
                "contract_type": "DIGITDIFF",
                "currency": "USD",
                "duration": 1,
                "duration_unit": "t",  # 1 tick
                "symbol": symbol,
                "barrier": str(barrier),
                "req_id": self._next_req_id()
            }
            
            logger.info("📤 Solicitando proposta...")
            await self.ws.send(json.dumps(proposal_request))
            response = await self.ws.recv()
            data = json.loads(response)
            
            if 'error' in data:
                logger.error(f"❌ Erro na proposta: {data['error']['message']}")
                return None
            
            if 'proposal' not in data:
                logger.error("❌ Sem proposta na resposta")
                return None
            
            proposal_id = data['proposal']['id']
            payout = data['proposal'].get('payout', 0)
            
            logger.info(f"✅ Proposta recebida!")
            logger.info(f"   ID: {proposal_id}")
            logger.info(f"   Payout: ${payout}")
            
            # Agora compra o contrato
            buy_request = {
                "buy": proposal_id,
                "price": float(amount),
                "req_id": self._next_req_id()
            }
            
            logger.info("💳 Comprando...")
            await self.ws.send(json.dumps(buy_request))
            buy_response = await self.ws.recv()
            buy_data = json.loads(buy_response)
            
            if 'error' in buy_data:
                logger.error(f"❌ Erro na compra: {buy_data['error']['message']}")
                return None
            
            if 'buy' in buy_data:
                contract_id = buy_data['buy']['contract_id']
                buy_price = buy_data['buy']['buy_price']
                
                logger.info("="*50)
                logger.info("🎉 CONTRATO COMPRADO!")
                logger.info(f"   ID: {contract_id}")
                logger.info(f"   Preço: ${buy_price}")
                logger.info("="*50)
                
                return {
                    'contract_id': contract_id,
                    'buy_price': buy_price,
                    'payout': payout
                }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Erro ao comprar DIGITDIFF: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    async def check_result(self, contract_id):
        """Verifica o resultado do contrato."""
        try:
            request = {
                "proposal_open_contract": 1,
                "contract_id": contract_id,
                "subscribe": 1,
                "req_id": self._next_req_id()
            }
            
            logger.info(f"⏳ Aguardando resultado do contrato {contract_id}...")
            await self.ws.send(json.dumps(request))
            
            # Aguarda até 30 segundos pelo resultado
            for i in range(30):
                try:
                    response = await asyncio.wait_for(self.ws.recv(), timeout=1)
                    data = json.loads(response)
                    
                    if 'proposal_open_contract' in data:
                        contract = data['proposal_open_contract']
                        
                        if contract.get('is_sold'):
                            profit = contract.get('profit', 0)
                            status = 'WIN' if profit > 0 else 'LOSS'
                            
                            logger.info("="*50)
                            logger.info(f"📊 RESULTADO: {status}")
                            logger.info(f"   Lucro: ${profit:.2f}")
                            logger.info("="*50)
                            
                            return {
                                'status': status,
                                'profit': profit
                            }
                except asyncio.TimeoutError:
                    continue
            
            logger.warning("⏰ Timeout aguardando resultado")
            return None
            
        except Exception as e:
            logger.error(f"Erro ao verificar resultado: {e}")
            return None
    
    async def disconnect(self):
        """Desconecta do WebSocket."""
        try:
            if self.ws:
                await self.ws.close()
                logger.info("🔌 Desconectado")
        except:
            pass
    
    def is_connected(self):
        return self.connected
    
    def is_authorized(self):
        return self.authorized
