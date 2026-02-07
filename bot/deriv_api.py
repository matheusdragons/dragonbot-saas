"""
Conexão com a API da Deriv
"""
import asyncio
import json
import websockets

class DerivAPI:
    
    def __init__(self, app_id="1089", token=None):
        self.app_id = app_id
        self.token = token
        self.ws = None
        self.url = f"wss://ws.binaryws.com/websockets/v3?app_id={app_id}"
    
    
    async def connect(self):
        """Conecta ao WebSocket da Deriv"""
        self.ws = await websockets.connect(self.url)
        
        if self.token:
            await self.authorize()
        
        return True
    
    
    async def authorize(self):
        """Autoriza com token do usuário"""
        request = {
            "authorize": self.token
        }
        await self.ws.send(json.dumps(request))
        response = await self.ws.recv()
        return json.loads(response)
    
    
    async def get_candles(self, symbol="R_75", count=100, granularity=300):
        """
        Busca histórico de candles
        granularity: 300 = 5 minutos
        """
        request = {
            "ticks_history": symbol,
            "adjust_start_time": 1,
            "count": count,
            "end": "latest",
            "granularity": granularity,
            "style": "candles"
        }
        await self.ws.send(json.dumps(request))
        response = await self.ws.recv()
        data = json.loads(response)
        
        if 'candles' in data:
            return data['candles']
        return []
    
    
    async def get_ticks(self, symbol="R_75", count=50):
        """
        Busca histórico de ticks (preços instantâneos)
        NOVO: Para estratégia de probabilidade
        """
        request = {
            "ticks_history": symbol,
            "adjust_start_time": 1,
            "count": count,
            "end": "latest",
            "style": "ticks"
        }
        await self.ws.send(json.dumps(request))
        response = await self.ws.recv()
        data = json.loads(response)
        
        if 'history' in data:
            return data['history']['prices']
        return []
    
    
    async def buy_contract(self, contract_type, amount, duration=5, symbol="R_75", barrier=None):
        """
        Compra contrato
        contract_type: 'CALL', 'PUT', 'DIGITOVER', 'DIGITUNDER'
        duration: minutos ou ticks (dependendo do tipo)
        barrier: Para DIGITOVER/DIGITUNDER (0-9)
        """
        params = {
            "contract_type": contract_type,
            "currency": "USD",
            "symbol": symbol,
            "basis": "stake",
            "amount": amount
        }
        
        # Se for DIGIT, usa ticks
        if "DIGIT" in contract_type:
            params["duration"] = duration
            params["duration_unit"] = "t"
            if barrier is not None:
                params["barrier"] = str(barrier)
        else:
            params["duration"] = duration
            params["duration_unit"] = "m"
        
        request = {
            "buy": 1,
            "price": amount,
            "parameters": params
        }
        await self.ws.send(json.dumps(request))
        response = await self.ws.recv()
        return json.loads(response)
    
    
    async def get_balance(self):
        """Retorna saldo da conta"""
        request = {"balance": 1}
        await self.ws.send(json.dumps(request))
        response = await self.ws.recv()
        data = json.loads(response)
        
        if 'balance' in data:
            return data['balance']['balance']
        return 0
    
    
    async def disconnect(self):
        """Desconecta"""
        if self.ws:
            await self.ws.close()
