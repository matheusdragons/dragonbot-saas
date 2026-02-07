"""
DragonBot SaaS - API de Comunicação com Deriv
Versão: 3.0 - Suporte a DIGITDIFF
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
        
        logger.info(f"🔌 DerivAPI inicializada | App ID: {app_id}")
    
    def _next_req_id(self):
        self.req_id += 1
        return self.req_id
    
    async def connect(self):
        try:
            logger.info(f"🔌 Conectando à Deriv...")
            self.ws = await websockets.connect(
                self.base_url,
                ping_interval=30,
                ping_timeout=10,
                close_timeout=5
            )
            self.connected = True
            logger.info("✅ WebSocket conectado!")
            
            if self.token:
                auth_result = await self.authorize()
                if not auth_result:
                    logger.error("❌ Falha na autorização!")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao conectar: {e}")
            self.connected = False
            return False
    
    async def authorize(self):
        if not self.token:
            logger.error("❌ Token não fornecido")
            return None
        
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
                logger.error(f"❌ Erro auth: {data['error']['message']}")
                return None
            
            if 'authorize' in data:
                self.authorized = True
                self.account_info = data['authorize']
                balance = self.account_info.get('balance', 0)
                currency = self.account_info.get('currency', 'USD')
                
                logger.info(f"✅ Autorizado! Saldo: {balance} {currency}")
                return self.account_info
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Erro na autorização: {e}")
            return None
    
    async def get_balance(self):
        try:
            request = {
                "balance": 1,
                "subscribe": 0,
                "req_id": self._next_req_id()
            }
            
            await self.ws.send(json.dumps(request))
            response = await self.ws.recv()
            data = json.loads(response)
            
            if 'error' in data:
                logger.error(f"❌ Erro saldo: {data['error']['message']}")
                return None
            
            if 'balance' in data:
                return {
                    'balance': data['balance']['balance'],
                    'currency': data['balance']['currency']
                }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar saldo: {e}")
            return None
    
    async def get_ticks(self, symbol="R_10", count=20):
        """Busca histórico de ticks."""
        try:
            request = {
                "ticks_history": symbol,
                "style": "ticks",
                "end": "latest",
                "count": count,
                "req_id": self._next_req_id()
            }
            
            logger.info(f"📊 Buscando ticks de {symbol}...")
            await self.ws.send(json.dumps(request))
            response = await self.ws.recv()
            data = json.loads(response)
            
            if 'error' in data:
                logger.error(f"❌ Erro ticks: {data['error']['message']}")
                return None
            
            if 'history' in data:
                prices = data['history'].get('prices', [])
                times = data['history'].get('times', [])
                
                ticks = []
                for i, price in enumerate(prices):
                    ticks.append({
                        'quote': float(price),
                        'epoch': times[i] if i < len(times) else None
                    })
                
                logger.info(f"✅ Recebidos {len(ticks)} ticks")
                if ticks:
                    logger.info(f"   Último: {ticks[-1]['quote']}")
                
                return ticks
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar ticks: {e}")
            return None
    
    async def buy_contract(self, contract_type, amount, duration=5, symbol="R_10", 
                          duration_unit="t", barrier=None):
        """
        Compra um contrato.
        
        contract_type: DIGITDIFF, DIGITMATCH, DIGITOVER, DIGITUNDER, etc
        barrier: Para DIGITDIFF, é o dígito que NÃO deve aparecer (0-9)
        """
        try:
            # Monta proposta
            proposal = {
                "proposal": 1,
                "amount": float(amount),
                "basis": "stake",
                "contract_type": contract_type,
                "currency": "USD",
                "duration": int(duration),
                "duration_unit": duration_unit,
                "symbol": symbol,
                "req_id": self._next_req_id()
            }
            
            # Adiciona barrier (obrigatório para DIGIT*)
            if barrier is not None:
                proposal["barrier"] = str(barrier)
            
            logger.info(f"📝 Proposta: {contract_type}")
            logger.info(f"   Ativo: {symbol}")
            logger.info(f"   Valor: ${amount}")
            logger.info(f"   Duração: {duration} ticks")
            logger.info(f"   Barrier: {barrier}")
            
            # Envia proposta
            await self.ws.send(json.dumps(proposal))
            response = await self.ws.recv()
            data = json.loads(response)
            
            if 'error' in data:
                error_msg = data['error'].get('message', 'Erro desconhecido')
                logger.error(f"❌ Erro proposta: {error_msg}")
                return None
            
            if 'proposal' not in data:
                logger.error(f"❌ Resposta sem proposta: {data}")
                return None
            
            proposal_id = data['proposal']['id']
            payout = data['proposal'].get('payout', 0)
            
            logger.info(f"✅ Proposta recebida! Payout: ${payout}")
            
            # Compra
            buy_request = {
                "buy": proposal_id,
                "price": float(amount),
                "req_id": self._next_req_id()
            }
            
            logger.info("💰 Comprando contrato...")
            await self.ws.send(json.dumps(buy_request))
            buy_response = await self.ws.recv()
            buy_data = json.loads(buy_response)
            
            if 'error' in buy_data:
                error_msg = buy_data['error'].get('message', 'Erro desconhecido')
                logger.error(f"❌ Erro compra: {error_msg}")
                return None
            
            if 'buy' in buy_data:
                contract = buy_data['buy']
                contract_id = contract.get('contract_id')
                buy_price = contract.get('buy_price', amount)
                
                logger.info(f"🎉 CONTRATO COMPRADO!")
                logger.info(f"   ID: {contract_id}")
                logger.info(f"   Preço: ${buy_price}")
                
                return {
                    'contract_id': contract_id,
                    'buy_price': buy_price,
                    'payout': payout,
                    'contract_type': contract_type,
                    'symbol': symbol,
                    'barrier': barrier
                }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Erro ao comprar: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    async def check_contract_result(self, contract_id, timeout=60):
        """Aguarda resultado do contrato."""
        try:
            request = {
                "proposal_open_contract": 1,
                "contract_id": contract_id,
                "subscribe": 1,
                "req_id": self._next_req_id()
            }
            
            logger.info(f"⏳ Aguardando resultado...")
            await self.ws.send(json.dumps(request))
            
            start_time = asyncio.get_event_loop().time()
            
            while True:
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > timeout:
                    logger.warning(f"⏰ Timeout!")
                    return None
                
                try:
                    response = await asyncio.wait_for(self.ws.recv(), timeout=5)
                    data = json.loads(response)
                    
                    if 'proposal_open_contract' in data:
                        contract = data['proposal_open_contract']
                        status = contract.get('status')
                        is_sold = contract.get('is_sold')
                        
                        if status == 'sold' or is_sold:
                            profit = contract.get('profit', 0)
                            result = 'WIN' if profit > 0 else 'LOSS'
                            
                            logger.info(f"📊 RESULTADO: {result} | ${profit:.2f}")
                            
                            return {
                                'status': result,
                                'profit': profit,
                                'contract_id': contract_id
                            }
                        
                except asyncio.TimeoutError:
                    continue
                    
        except Exception as e:
            logger.error(f"❌ Erro ao verificar contrato: {e}")
            return None
    
    async def disconnect(self):
        try:
            if self.ws:
                await self.ws.close()
                self.connected = False
                self.authorized = False
                logger.info("🔌 Desconectado")
        except Exception as e:
            logger.error(f"❌ Erro ao desconectar: {e}")
    
    def is_connected(self):
        return self.connected and self.ws and not self.ws.closed
    
    def is_authorized(self):
        return self.authorized
