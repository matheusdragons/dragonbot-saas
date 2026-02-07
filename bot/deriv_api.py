"""
DragonBot SaaS - API de Comunicação com Deriv
Versão: 2.0 - Suporte a Ticks e Contratos DIGIT
"""

import json
import asyncio
import websockets
import logging

logger = logging.getLogger(__name__)


class DerivAPI:
    """
    Cliente WebSocket para API da Deriv.
    Suporta contratos CALL/PUT e DIGITOVER/DIGITUNDER.
    """
    
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
        """Gera próximo ID de requisição."""
        self.req_id += 1
        return self.req_id
    
    async def connect(self):
        """Estabelece conexão WebSocket."""
        try:
            logger.info(f"Conectando à Deriv API...")
            self.ws = await websockets.connect(
                self.base_url,
                ping_interval=30,
                ping_timeout=10,
                close_timeout=5
            )
            self.connected = True
            logger.info("Conectado ao WebSocket da Deriv")
            
            if self.token:
                await self.authorize()
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao conectar: {e}")
            self.connected = False
            return False
    
    async def authorize(self):
        """Autoriza com token da API."""
        if not self.token:
            logger.error("Token não fornecido")
            return None
        
        try:
            request = {
                "authorize": self.token,
                "req_id": self._next_req_id()
            }
            
            await self.ws.send(json.dumps(request))
            response = await self.ws.recv()
            data = json.loads(response)
            
            if 'error' in data:
                logger.error(f"Erro de autorização: {data['error']['message']}")
                return None
            
            if 'authorize' in data:
                self.authorized = True
                self.account_info = data['authorize']
                logger.info(f"Autorizado: {self.account_info.get('email', 'N/A')} | "
                          f"Saldo: {self.account_info.get('balance', 0)} {self.account_info.get('currency', 'USD')}")
                return self.account_info
            
            return None
            
        except Exception as e:
            logger.error(f"Erro na autorização: {e}")
            return None
    
    async def get_balance(self):
        """Retorna saldo atual da conta."""
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
                logger.error(f"Erro ao buscar saldo: {data['error']['message']}")
                return None
            
            if 'balance' in data:
                return {
                    'balance': data['balance']['balance'],
                    'currency': data['balance']['currency']
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Erro ao buscar saldo: {e}")
            return None
    
    async def get_ticks(self, symbol="R_75", count=50):
        """
        Busca histórico de ticks (preços individuais).
        """
        try:
            request = {
                "ticks_history": symbol,
                "style": "ticks",
                "end": "latest",
                "count": count,
                "req_id": self._next_req_id()
            }
            
            await self.ws.send(json.dumps(request))
            response = await self.ws.recv()
            data = json.loads(response)
            
            if 'error' in data:
                logger.error(f"Erro ao buscar ticks: {data['error']['message']}")
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
                
                logger.info(f"Recebidos {len(ticks)} ticks de {symbol}")
                return ticks
            
            return None
            
        except Exception as e:
            logger.error(f"Erro ao buscar ticks: {e}")
            return None
    
    async def get_candles(self, symbol="R_75", count=100, granularity=300):
        """Busca histórico de candles."""
        try:
            request = {
                "ticks_history": symbol,
                "style": "candles",
                "end": "latest",
                "count": count,
                "granularity": granularity,
                "req_id": self._next_req_id()
            }
            
            await self.ws.send(json.dumps(request))
            response = await self.ws.recv()
            data = json.loads(response)
            
            if 'error' in data:
                logger.error(f"Erro ao buscar candles: {data['error']['message']}")
                return None
            
            if 'candles' in data:
                candles = data['candles']
                logger.info(f"Recebidos {len(candles)} candles de {symbol}")
                return candles
            
            return None
            
        except Exception as e:
            logger.error(f"Erro ao buscar candles: {e}")
            return None
    
    async def buy_contract(self, contract_type, amount, duration=5, symbol="R_75", 
                          duration_unit="t", barrier=None):
        """
        Compra um contrato de opção.
        """
        try:
            proposal = {
                "proposal": 1,
                "amount": amount,
                "basis": "stake",
                "contract_type": contract_type,
                "currency": "USD",
                "duration": duration,
                "duration_unit": duration_unit,
                "symbol": symbol,
                "req_id": self._next_req_id()
            }
            
            if barrier is not None and "DIGIT" in contract_type:
                proposal["barrier"] = str(barrier)
            
            logger.info(f"Solicitando proposta: {contract_type} {symbol} ${amount} "
                       f"dur={duration}{duration_unit} barrier={barrier}")
            
            await self.ws.send(json.dumps(proposal))
            response = await self.ws.recv()
            data = json.loads(response)
            
            if 'error' in data:
                logger.error(f"Erro na proposta: {data['error']['message']}")
                return None
            
            if 'proposal' not in data:
                logger.error("Resposta sem proposta")
                return None
            
            proposal_id = data['proposal']['id']
            payout = data['proposal'].get('payout', 0)
            logger.info(f"Proposta recebida: ID={proposal_id} | Payout=${payout}")
            
            buy_request = {
                "buy": proposal_id,
                "price": amount,
                "req_id": self._next_req_id()
            }
            
            await self.ws.send(json.dumps(buy_request))
            buy_response = await self.ws.recv()
            buy_data = json.loads(buy_response)
            
            if 'error' in buy_data:
                logger.error(f"Erro na compra: {buy_data['error']['message']}")
                return None
            
            if 'buy' in buy_data:
                contract = buy_data['buy']
                contract_id = contract.get('contract_id')
                buy_price = contract.get('buy_price', amount)
                
                logger.info(f"CONTRATO COMPRADO: ID={contract_id} | Preço=${buy_price}")
                
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
            logger.error(f"Erro ao comprar contrato: {e}")
            return None
    
    async def check_contract_result(self, contract_id, timeout=60):
        """Aguarda e verifica resultado de um contrato."""
        try:
            request = {
                "proposal_open_contract": 1,
                "contract_id": contract_id,
                "subscribe": 1,
                "req_id": self._next_req_id()
            }
            
            await self.ws.send(json.dumps(request))
            
            start_time = asyncio.get_event_loop().time()
            
            while True:
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > timeout:
                    logger.warning(f"Timeout aguardando resultado do contrato {contract_id}")
                    return None
                
                try:
                    response = await asyncio.wait_for(self.ws.recv(), timeout=5)
                    data = json.loads(response)
                    
                    if 'proposal_open_contract' in data:
                        contract = data['proposal_open_contract']
                        status = contract.get('status')
                        
                        if status == 'sold' or contract.get('is_sold'):
                            profit = contract.get('profit', 0)
                            sell_price = contract.get('sell_price', 0)
                            
                            result = 'WIN' if profit > 0 else 'LOSS'
                            
                            logger.info(f"RESULTADO: {result} | Lucro: ${profit:.2f}")
                            
                            return {
                                'status': result,
                                'profit': profit,
                                'sell_price': sell_price,
                                'contract_id': contract_id
                            }
                        
                        current_profit = contract.get('profit', 0)
                        logger.debug(f"Contrato em aberto... Profit atual: ${current_profit:.2f}")
                        
                except asyncio.TimeoutError:
                    continue
                    
        except Exception as e:
            logger.error(f"Erro ao verificar contrato: {e}")
            return None
    
    async def get_account_list(self):
        """Lista todas as contas disponíveis."""
        try:
            request = {
                "account_list": 1,
                "req_id": self._next_req_id()
            }
            
            await self.ws.send(json.dumps(request))
            response = await self.ws.recv()
            data = json.loads(response)
            
            if 'account_list' in data:
                return data['account_list']
            
            return None
            
        except Exception as e:
            logger.error(f"Erro ao listar contas: {e}")
            return None
    
    async def disconnect(self):
        """Fecha conexão WebSocket."""
        try:
            if self.ws:
                await self.ws.close()
                self.connected = False
                self.authorized = False
                logger.info("Desconectado da Deriv API")
        except Exception as e:
            logger.error(f"Erro ao desconectar: {e}")
    
    def is_connected(self):
        """Verifica se está conectado."""
        return self.connected and self.ws and not self.ws.closed
    
    def is_authorized(self):
        """Verifica se está autorizado."""
        return self.authorized
