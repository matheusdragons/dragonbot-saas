"""
DragonBot SaaS - Robô do Dígito 7
Estratégia: Quando último dígito = 7, aposta DIGITDIFF
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
        
        # Configurações
        self.deriv_token = user_config.get('deriv_token')
        self.deriv_app_id = user_config.get('deriv_app_id', '1089')
        self.valor_entrada = float(user_config.get('valor_entrada', 1.0))
        self.stop_loss = float(user_config.get('stop_loss', 50.0))
        self.take_profit = float(user_config.get('take_profit', 100.0))
        self.max_operacoes = int(user_config.get('max_operacoes_dia', 20))
        
        # Ativo fixo R_10 (Volatility 10)
        self.ativo = 'R_10'
        
        # APIs
        self.api = DerivAPI(app_id=self.deriv_app_id, token=self.deriv_token)
        self.strategy = Strategy()
        
        # Estado
        self.running = False
        self.saldo_inicial = 0
        self.saldo_atual = 0
        
        # Contadores
        self.operacoes_hoje = 0
        self.wins = 0
        self.losses = 0
        self.lucro_total = 0
        
        # Logs
        self.logs = deque(maxlen=100)
        self.save_operation_callback = None
        self.save_log_callback = None
        
        logger.info(f"🤖 Robô do Dígito 7 iniciado - User: {self.user_id}")
    
    def log(self, tipo, mensagem):
        """Registra log."""
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
        """Inicia o robô."""
        self.log('INFO', '='*60)
        self.log('INFO', '🎯 DRAGONBOT - ESTRATÉGIA DO DÍGITO 7')
        self.log('INFO', '='*60)
        
        try:
            # CONECTA
            connected = await self.api.connect()
            if not connected:
                self.log('ERRO', '❌ Falha na conexão')
                return False
            
            self.log('INFO', '✅ Conectado à Deriv')
            
            # AUTORIZA
            if self.api.token and not self.api.is_authorized():
                self.log('ERRO', '❌ Falha na autorização')
                return False
            
            # PEGA SALDO
            if self.api.is_authorized():
                balance = await self.api.get_balance()
                if balance:
                    self.saldo_inicial = balance['balance']
                    self.saldo_atual = self.saldo_inicial
                    self.log('INFO', f'💰 Saldo: ${self.saldo_inicial:.2f} {balance["currency"]}')
            
            # INICIA
            self.running = True
            self.log('INFO', '✅ Robô ativo!')
            self.log('INFO', f'📊 Ativo: {self.ativo}')
            self.log('INFO', f'💵 Entrada: ${self.valor_entrada}')
            self.log('INFO', '🎯 Estratégia: Se dígito = 7, aposta DIGITDIFF')
            self.log('INFO', '='*60)
            
            # LOOP PRINCIPAL
            await self.run_loop()
            return True
            
        except Exception as e:
            self.log('ERRO', f'❌ Erro: {e}')
            return False
    
    async def run_loop(self):
        """Loop principal que procura o dígito 7."""
        
        checks_without_seven = 0
        
        while self.running and self.operacoes_hoje < self.max_operacoes:
            try:
                # BUSCA TICKS
                ticks = await self.api.get_ticks(symbol=self.ativo, count=5)
                
                if not ticks:
                    self.log('ERRO', '❌ Sem dados de ticks')
                    await asyncio.sleep(5)
                    continue
                
                # ANALISA
                signal = self.strategy.analyze(ticks)
                
                if signal:
                    # ENCONTROU O 7!
                    self.log('SINAL', '🎯 DÍGITO 7 DETECTADO!')
                    
                    # EXECUTA TRADE
                    success = await self.execute_digitdiff_trade()
                    
                    if success:
                        self.log('INFO', '✅ Trade executado!')
                        # Espera um pouco após executar
                        await asyncio.sleep(10)
                    else:
                        self.log('ERRO', '❌ Falha no trade')
                        await asyncio.sleep(5)
                    
                    checks_without_seven = 0
                else:
                    # NÃO É 7, CONTINUA PROCURANDO
                    checks_without_seven += 1
                    
                    if checks_without_seven % 10 == 0:
                        self.log('INFO', f'⏳ {checks_without_seven} verificações sem encontrar 7...')
                    
                    # Espera 2 segundos e verifica novamente
                    await asyncio.sleep(2)
                
                # VERIFICA LIMITES
                if self.lucro_total <= -self.stop_loss:
                    self.log('INFO', f'🛑 Stop Loss: ${self.lucro_total:.2f}')
                    break
                
                if self.lucro_total >= self.take_profit:
                    self.log('INFO', f'🎉 Take Profit: ${self.lucro_total:.2f}')
                    break
                    
            except Exception as e:
                self.log('ERRO', f'❌ Erro no loop: {e}')
                await asyncio.sleep(5)
        
        # FINALIZA
        self.log('INFO', '='*60)
        self.log('INFO', '🏁 Sessão finalizada')
        self.log('INFO', f'📊 Resultado: {self.wins}W / {self.losses}L')
        self.log('INFO', f'💰 Lucro: ${self.lucro_total:.2f}')
        self.log('INFO', '='*60)
        
        await self.api.disconnect()
    
    async def execute_digitdiff_trade(self):
        """Executa trade DIGITDIFF quando encontra o 7."""
        try:
            self.log('ENTRADA', '='*50)
            self.log('ENTRADA', '💰 EXECUTANDO DIGITDIFF')
            self.log('ENTRADA', f'   Barrier: 7 (aposta que próximo ≠ 7)')
            self.log('ENTRADA', f'   Valor: ${self.valor_entrada:.2f}')
            self.log('ENTRADA', '='*50)
            
            # COMPRA DIGITDIFF
            contract = await self.api.buy_digitdiff(
                amount=self.valor_entrada,
                barrier=7,
                symbol=self.ativo
            )
            
            if not contract:
                self.log('ERRO', '❌ Falha ao comprar DIGITDIFF')
                self.operacoes_hoje += 1
                self.losses += 1
                self.lucro_total -= self.valor_entrada
                return False
            
            contract_id = contract['contract_id']
            self.operacoes_hoje += 1
            
            # AGUARDA RESULTADO
            result = await self.api.check_result(contract_id)
            
            if result:
                profit = result['profit']
                status = result['status']
                
                if status == 'WIN':
                    self.wins += 1
                    self.log('RESULTADO', f'🎉 WIN! Próximo ≠ 7 | +${profit:.2f}')
                else:
                    self.losses += 1
                    self.log('RESULTADO', f'😔 LOSS! Próximo = 7 | ${profit:.2f}')
                
                self.lucro_total += profit
                self.saldo_atual = self.saldo_inicial + self.lucro_total
                
                # Salva no banco
                if self.save_operation_callback:
                    try:
                        self.save_operation_callback(
                            user_id=self.user_id,
                            tipo='DIGITDIFF',
                            ativo=self.ativo,
                            valor=self.valor_entrada,
                            resultado=status,
                            lucro=profit,
                            barrier='7',
                            confianca=0.90
                        )
                    except:
                        pass
                
                # Estatísticas
                total = self.wins + self.losses
                win_rate = (self.wins / total * 100) if total > 0 else 0
                
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
        win_rate = (self.wins / (self.wins + self.losses) * 100) if (self.wins + self.losses) > 0 else 0
        
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
            'logs': list(self.logs)[-20:],
            'strategy': 'DIGIT_7'
        }
