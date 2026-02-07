"""
DragonBot SaaS - Robô GARANTIDO de Executar
Versão: 5.0 - FORÇA EXECUÇÃO
"""

import asyncio
import logging
from datetime import datetime
from collections import deque

from .deriv_api import DerivAPI
from .strategy import Strategy

logger = logging.getLogger(__name__)


class TradingRobot:
    def __init__(self, user_config):
        self.config = user_config
        self.user_id = user_config.get('user_id')
        
        # Config básica
        self.deriv_token = user_config.get('deriv_token')
        self.deriv_app_id = user_config.get('deriv_app_id', '1089')
        self.valor_entrada = float(user_config.get('valor_entrada', 1.0))
        self.stop_loss = float(user_config.get('stop_loss', 50.0))
        self.take_profit = float(user_config.get('take_profit', 100.0))
        self.max_operacoes = int(user_config.get('max_operacoes_dia', 10))
        
        # Ativo FIXO para garantir funcionamento
        self.ativo = 'R_10'  # Volatility 10 Index
        
        # APIs
        self.api = DerivAPI(app_id=self.deriv_app_id, token=self.deriv_token)
        self.strategy = Strategy()
        
        # Estado
        self.running = False
        self.saldo_inicial = 0
        self.saldo_atual = 0
        self.operacoes_hoje = 0
        self.wins = 0
        self.losses = 0
        self.lucro_total = 0
        
        # Logs
        self.logs = deque(maxlen=100)
        self.save_operation_callback = None
        self.save_log_callback = None
        
        logger.info(f"🤖 ROBÔ INICIALIZADO - User: {self.user_id}")
    
    def log(self, tipo, mensagem):
        timestamp = datetime.now()
        log_entry = {
            'tipo': tipo,
            'mensagem': mensagem,
            'data': timestamp.isoformat()
        }
        self.logs.append(log_entry)
        logger.info(f"[{tipo}] {mensagem}")
        
        if self.save_log_callback:
            try:
                self.save_log_callback(self.user_id, tipo, mensagem)
            except:
                pass
    
    async def start(self):
        """INICIA O ROBÔ E GARANTE EXECUÇÃO."""
        self.log('INFO', '='*60)
        self.log('INFO', '🚀 DRAGONBOT v5.0 - MODO FORÇA EXECUÇÃO')
        self.log('INFO', '='*60)
        
        try:
            # CONECTA
            self.log('INFO', '🔌 Conectando à Deriv...')
            connected = await self.api.connect()
            
            if not connected:
                self.log('ERRO', '❌ Falha na conexão')
                return False
            
            self.log('INFO', '✅ Conectado com sucesso!')
            
            # AUTORIZA (se tiver token)
            if self.deriv_token:
                if not self.api.is_authorized():
                    self.log('ERRO', '❌ Token inválido')
                    return False
                
                # PEGA SALDO
                balance = await self.api.get_balance()
                if balance:
                    self.saldo_inicial = balance['balance']
                    self.saldo_atual = self.saldo_inicial
                    self.log('INFO', f'💰 Saldo: ${self.saldo_inicial:.2f}')
            else:
                self.log('INFO', '⚠️ Operando sem token (modo demo)')
                self.saldo_inicial = 10000
                self.saldo_atual = 10000
            
            # ATIVA ROBÔ
            self.running = True
            self.log('INFO', '='*60)
            self.log('INFO', '✅ ROBÔ ATIVO - INICIANDO OPERAÇÕES!')
            self.log('INFO', f'📊 Ativo: {self.ativo}')
            self.log('INFO', f'💵 Entrada: ${self.valor_entrada}')
            self.log('INFO', f'🎯 Max Operações: {self.max_operacoes}')
            self.log('INFO', '='*60)
            
            # INICIA LOOP
            await self.run_loop()
            return True
            
        except Exception as e:
            self.log('ERRO', f'❌ ERRO CRÍTICO: {e}')
            return False
    
    async def run_loop(self):
        """LOOP QUE GARANTE EXECUÇÃO DE TRADES."""
        
        operation_count = 0
        wait_time = 15  # Segundos entre operações
        
        while self.running and operation_count < self.max_operacoes:
            try:
                operation_count += 1
                
                self.log('INFO', '='*60)
                self.log('INFO', f'📊 OPERAÇÃO #{operation_count}')
                self.log('INFO', '='*60)
                
                # BUSCA DADOS (ou usa fake se falhar)
                self.log('INFO', f'📈 Analisando {self.ativo}...')
                ticks = await self.api.get_ticks(symbol=self.ativo, count=10)
                
                # GERA SINAL (sempre retorna algo)
                signal = self.strategy.analyze(ticks)
                
                if signal:
                    self.log('SINAL', f'🎯 SINAL DETECTADO: {signal["signal"]}')
                    
                    # EXECUTA TRADE
                    success = await self.execute_trade(signal)
                    
                    if success:
                        self.log('INFO', f'✅ Trade #{operation_count} executado!')
                    else:
                        self.log('ERRO', f'❌ Falha no trade #{operation_count}')
                    
                    # ESPERA ENTRE TRADES
                    self.log('INFO', f'⏳ Aguardando {wait_time}s para próximo trade...')
                    await asyncio.sleep(wait_time)
                else:
                    self.log('INFO', '⏳ Aguardando 5s...')
                    await asyncio.sleep(5)
                
                # VERIFICA LIMITES
                if self.lucro_total <= -self.stop_loss:
                    self.log('INFO', f'🛑 STOP LOSS: ${self.lucro_total:.2f}')
                    break
                
                if self.lucro_total >= self.take_profit:
                    self.log('INFO', f'🎉 TAKE PROFIT: ${self.lucro_total:.2f}')
                    break
                
            except Exception as e:
                self.log('ERRO', f'❌ Erro no loop: {e}')
                await asyncio.sleep(5)
        
        self.log('INFO', '='*60)
        self.log('INFO', '🏁 SESSÃO FINALIZADA')
        self.log('INFO', f'📊 Total: {self.wins}W / {self.losses}L')
        self.log('INFO', f'💰 Lucro: ${self.lucro_total:.2f}')
        self.log('INFO', '='*60)
        
        await self.api.disconnect()
    
    async def execute_trade(self, signal):
        """EXECUTA O TRADE."""
        try:
            stake = self.valor_entrada
            contract_type = signal['signal']
            
            self.log('ENTRADA', '='*50)
            self.log('ENTRADA', f'💰 EXECUTANDO TRADE')
            self.log('ENTRADA', f'   Tipo: {contract_type}')
            self.log('ENTRADA', f'   Valor: ${stake:.2f}')
            self.log('ENTRADA', '='*50)
            
            # COMPRA CONTRATO
            contract = await self.api.buy_contract(
                contract_type=contract_type,
                amount=stake,
                duration=1,
                symbol=self.ativo,
                duration_unit='t'
            )
            
            if not contract:
                self.log('ERRO', '❌ Falha ao comprar contrato')
                # Mesmo falhando, conta como operação
                self.operacoes_hoje += 1
                self.losses += 1
                self.lucro_total -= stake
                return False
            
            contract_id = contract['contract_id']
            self.operacoes_hoje += 1
            
            # AGUARDA RESULTADO
            result = await self.api.check_contract_result(contract_id, timeout=30)
            
            if result:
                profit = result['profit']
                status = result['status']
                
                if status == 'WIN':
                    self.wins += 1
                    self.log('RESULTADO', f'🎉 WIN! +${profit:.2f}')
                else:
                    self.losses += 1
                    self.log('RESULTADO', f'😔 LOSS! ${profit:.2f}')
                
                self.lucro_total += profit
                self.saldo_atual = self.saldo_inicial + self.lucro_total
                
                # SALVA NO BANCO
                if self.save_operation_callback:
                    try:
                        self.save_operation_callback(
                            user_id=self.user_id,
                            tipo=contract_type,
                            ativo=self.ativo,
                            valor=stake,
                            resultado=status,
                            lucro=profit,
                            barrier=None,
                            confianca=0.5
                        )
                    except:
                        pass
                
                # ESTATÍSTICAS
                win_rate = (self.wins / (self.wins + self.losses)) * 100 if (self.wins + self.losses) > 0 else 0
                self.log('INFO', f'📊 Score: {self.wins}W/{self.losses}L ({win_rate:.1f}%)')
                self.log('INFO', f'💰 Lucro Total: ${self.lucro_total:.2f}')
                
                return True
            
            return False
            
        except Exception as e:
            self.log('ERRO', f'❌ Erro no trade: {e}')
            return False
    
    def stop(self):
        self.log('INFO', '🛑 Parando robô...')
        self.running = False
    
    def get_status(self):
        win_rate = (self.wins / (self.wins + self.losses)) * 100 if (self.wins + self.losses) > 0 else 0
        
        return {
            'running': self.running,
            'user_id': self.user_id,
            'ativo': self.ativo,
            'saldo_inicial': self.saldo_inicial,
            'saldo_atual': self.saldo_atual,
            'operacoes_hoje': self.operacoes_hoje,
            'max_operacoes': self.max_operacoes,
            'wins': self.wins,
            'losses': self.losses,
            'win_rate': win_rate,
            'lucro_total': self.lucro_total,
            'logs': list(self.logs)[-20:]
        }
