"""
Robô de Trading - Gerenciador principal
"""
import asyncio
from datetime import datetime, timedelta
from bot.deriv_api import DerivAPI
from bot.strategy import Strategy
from bot.strategy_probability import StrategyProbability

class TradingRobot:
    
    def __init__(self, user_config):
        self.config = user_config
        self.api = DerivAPI(
            app_id=user_config.get('app_id', '1089'),
            token=user_config.get('token')
        )
        
        # Escolhe estratégia baseado na config do usuário
        estrategia_tipo = user_config.get('estrategia_tipo', 'technical')
        
        if estrategia_tipo == 'probability':
            self.strategy = StrategyProbability()
            self.use_ticks = True
            self.cycle_time = 10
            self.wait_result = 20
        else:
            self.strategy = Strategy()
            self.use_ticks = False
            self.cycle_time = 30
            self.wait_result = 310
        
        self.running = False
        self.logs = []
        
        # Controle diário
        self.operacoes_hoje = 0
        self.lucro_dia = 0
        self.prejuizo_dia = 0
    
    
    def log(self, tipo, mensagem):
        """Adiciona log"""
        entry = {
            'tipo': tipo,
            'mensagem': mensagem,
            'data': datetime.now().strftime('%H:%M:%S')
        }
        self.logs.append(entry)
        
        if len(self.logs) > 100:
            self.logs = self.logs[-100:]
        
        return entry
    
    
    async def start(self):
        """Inicia o robô"""
        self.running = True
        
        estrategia_nome = 'Probabilidade (Over/Under)' if self.use_ticks else 'Técnica (BB+RSI+VC)'
        self.log('INFO', f'Robô iniciando com estratégia: {estrategia_nome}')
        
        try:
            await self.api.connect()
            self.log('INFO', 'Conectado à Deriv ✓')
            
            balance = await self.api.get_balance()
            self.log('INFO', f'Saldo: ${balance:.2f}')
            
            await self.run_loop()
            
        except Exception as e:
            self.log('ERRO', f'Erro: {str(e)}')
            self.running = False
    
    
    async def run_loop(self):
        """Loop principal de operação"""
        while self.running:
            try:
                # Verifica limites
                if self.operacoes_hoje >= self.config.get('max_operacoes', 50):
                    self.log('INFO', 'Limite diário atingido. Aguardando...')
                    await asyncio.sleep(60)
                    continue
                
                if self.prejuizo_dia >= self.config.get('stop_loss', 50):
                    self.log('INFO', f'Stop Loss atingido: -${self.prejuizo_dia:.2f}')
                    self.running = False
                    break
                
                if self.lucro_dia >= self.config.get('take_profit', 100):
                    self.log('INFO', f'Take Profit atingido: +${self.lucro_dia:.2f}')
                    self.running = False
                    break
                
                
                # Busca dados baseado na estratégia
                if self.use_ticks:
                    data = await self.api.get_ticks(symbol='R_75', count=50)
                    data_type = 'ticks'
                else:
                    data = await self.api.get_candles(symbol='R_75', count=100, granularity=300)
                    data_type = 'candles'
                
                if not data:
                    self.log('ERRO', f'Sem dados de {data_type}')
                    await asyncio.sleep(10)
                    continue
                
                
                # Analisa estratégia
                signal = self.strategy.analyze(data)
                
                if signal:
                    self.log('SINAL', f'{signal["signal"]} detectado!')
                    self.log('INFO', signal['reason'])
                    
                    # Executa operação
                    await self.execute_trade(signal)
                
                
                # Aguarda próximo ciclo
                await asyncio.sleep(self.cycle_time)
                
            except Exception as e:
                self.log('ERRO', f'Erro no loop: {str(e)}')
                await asyncio.sleep(10)
    
    
    async def execute_trade(self, signal):
        """Executa uma operação"""
        try:
            contract_type = signal['signal']
            amount = self.config.get('valor_entrada', 1.0)
            
            self.log('ENTRADA', f'{contract_type} - ${amount:.2f}')
            
            # Prepara argumentos
            kwargs = {
                'contract_type': contract_type,
                'amount': amount,
                'duration': 5,
                'symbol': 'R_75'
            }
            
            # Se tem barrier (DIGITOVER/DIGITUNDER)
            if 'barrier' in signal:
                kwargs['barrier'] = signal['barrier']
                self.log('INFO', f'Barrier: {signal["barrier"]}')
            
            result = await self.api.buy_contract(**kwargs)
            
            if 'buy' in result:
                contract_id = result['buy']['contract_id']
                self.log('INFO', f'Contrato: {contract_id}')
                self.operacoes_hoje += 1
                
                # Aguarda resultado
                await asyncio.sleep(self.wait_result)
                
                self.log('INFO', 'Aguardando resultado...')
                
            else:
                self.log('ERRO', f'Erro na compra: {result}')
                
        except Exception as e:
            self.log('ERRO', f'Erro ao executar: {str(e)}')
    
    
    def stop(self):
        """Para o robô"""
        self.running = False
        self.log('INFO', 'Robô parado pelo usuário')
    
    
    def get_status(self):
        """Retorna status atual"""
        return {
            'running': self.running,
            'operacoes_hoje': self.operacoes_hoje,
            'lucro_dia': self.lucro_dia,
            'prejuizo_dia': self.prejuizo_dia,
            'logs': self.logs[-20:]
        }
