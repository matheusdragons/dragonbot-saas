"""
DragonBot SaaS - Motor Principal do Robô
Versão: 2.1 - DEBUG MODE
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
        
        self.deriv_token = user_config.get('deriv_token')
        self.deriv_app_id = user_config.get('deriv_app_id', '1089')
        self.valor_entrada = float(user_config.get('valor_entrada', 1.0))
        self.stop_loss = float(user_config.get('stop_loss', 50.0))
        self.take_profit = float(user_config.get('take_profit', 100.0))
        self.max_operacoes = int(user_config.get('max_operacoes_dia', 50))
        self.ativo = user_config.get('ativo', 'R_75')
        
        self.tipo_gestao = user_config.get('tipo_gestao', 'fixo')
        self.nivel_martingale = float(user_config.get('nivel_martingale', 2.0))
        
        self.api = DerivAPI(app_id=self.deriv_app_id, token=self.deriv_token)
        self.strategy = Strategy()
        
        self.running = False
        self.paused = False
        self.saldo_inicial = 0
        self.saldo_atual = 0
        
        self.operacoes_hoje = 0
        self.wins = 0
        self.losses = 0
        self.lucro_total = 0
        self.sequencia_loss = 0
        self.maior_sequencia_loss = 0
        self.valor_atual = self.valor_entrada
        
        self.logs = deque(maxlen=100)
        self.save_operation_callback = None
        self.save_log_callback = None
        
        logger.info(f"🤖 TradingRobot inicializado")
        logger.info(f"   User ID: {self.user_id}")
        logger.info(f"   Ativo: {self.ativo}")
        logger.info(f"   Entrada: ${self.valor_entrada}")
        logger.info(f"   Stop Loss: ${self.stop_loss}")
        logger.info(f"   Take Profit: ${self.take_profit}")
    
    def log(self, tipo, mensagem):
        timestamp = datetime.now()
        log_entry = {
            'tipo': tipo,
            'mensagem': mensagem,
            'data': timestamp.isoformat(),
            'timestamp': timestamp
        }
        
        self.logs.append(log_entry)
        
        # Emoji baseado no tipo
        emoji = {
            'INFO': 'ℹ️',
            'SINAL': '🎯',
            'ENTRADA': '📈',
            'RESULTADO': '📊',
            'ERRO': '❌'
        }.get(tipo, '📝')
        
        log_func = logger.error if tipo == 'ERRO' else logger.info
        log_func(f"{emoji} [{tipo}] {mensagem}")
        
        if self.save_log_callback:
            try:
                self.save_log_callback(self.user_id, tipo, mensagem)
            except Exception as e:
                logger.error(f"Erro ao salvar log: {e}")
    
    async def start(self):
        self.log('INFO', '🚀 Iniciando DragonBot v2.1 DEBUG...')
        
        try:
            # Conecta
            self.log('INFO', 'Conectando à Deriv API...')
            connected = await self.api.connect()
            
            if not connected:
                self.log('ERRO', 'Falha ao conectar na Deriv API')
                return False
            
            self.log('INFO', 'Conectado! Verificando autorização...')
            
            if not self.api.is_authorized():
                self.log('ERRO', 'Falha na autorização - verifique seu token')
                return False
            
            # Saldo
            self.log('INFO', 'Buscando saldo...')
            balance_info = await self.api.get_balance()
            
            if balance_info:
                self.saldo_inicial = balance_info['balance']
                self.saldo_atual = self.saldo_inicial
                self.log('INFO', f'💰 Saldo: ${self.saldo_inicial:.2f} {balance_info["currency"]}')
            else:
                self.log('ERRO', 'Não foi possível obter saldo')
                return False
            
            # Inicia
            self.running = True
            self.log('INFO', f'✅ Robô iniciado!')
            self.log('INFO', f'📊 Ativo: {self.ativo}')
            self.log('INFO', f'💵 Entrada: ${self.valor_entrada}')
            self.log('INFO', f'🎯 Estratégia: DIGIT (Over/Under)')
            
            # Loop principal
            await self.run_loop()
            return True
            
        except Exception as e:
            self.log('ERRO', f'Erro ao iniciar: {str(e)}')
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    async def run_loop(self):
        self.log('INFO', '🔄 Iniciando loop de trading...')
        
        loop_count = 0
        
        while self.running:
            try:
                loop_count += 1
                self.log('INFO', f'--- Loop #{loop_count} ---')
                
                # Verifica limites
                if not self._check_limits():
                    self.log('INFO', 'Limite atingido, parando...')
                    break
                
                # Pausa
                if self.paused:
                    self.log('INFO', 'Robô pausado, aguardando...')
                    await asyncio.sleep(5)
                    continue
                
                # Busca ticks
                self.log('INFO', f'Buscando ticks de {self.ativo}...')
                ticks = await self.api.get_ticks(symbol=self.ativo, count=30)
                
                if not ticks:
                    self.log('ERRO', 'Falha ao buscar ticks!')
                    await asyncio.sleep(10)
                    continue
                
                self.log('INFO', f'Recebidos {len(ticks)} ticks')
                
                # Analisa
                self.log('INFO', 'Analisando estratégia...')
                signal = self.strategy.analyze(ticks)
                
                if signal:
                    self.log('SINAL', f"{signal['signal']} | Barrier: {signal['barrier']}")
                    self.log('SINAL', f"Confiança: {signal['confidence']:.1%}")
                    self.log('SINAL', f"Razão: {signal['reason']}")
                    
                    # Executa trade
                    self.log('INFO', 'Executando trade...')
                    await self.execute_trade(signal)
                else:
                    self.log('INFO', 'Nenhum sinal gerado')
                
                # Intervalo
                self.log('INFO', 'Aguardando 15 segundos...')
                await asyncio.sleep(15)
                
            except asyncio.CancelledError:
                self.log('INFO', 'Loop cancelado')
                break
            except Exception as e:
                self.log('ERRO', f'Erro no loop: {str(e)}')
                import traceback
                logger.error(traceback.format_exc())
                await asyncio.sleep(10)
        
        self.log('INFO', '🛑 Loop finalizado')
        await self.api.disconnect()
    
    def _check_limits(self):
        if self.operacoes_hoje >= self.max_operacoes:
            self.log('INFO', f'Max operações: {self.operacoes_hoje}/{self.max_operacoes}')
            self.running = False
            return False
        
        if self.lucro_total <= -self.stop_loss:
            self.log('INFO', f'Stop Loss: ${self.lucro_total:.2f}')
            self.running = False
            return False
        
        if self.lucro_total >= self.take_profit:
            self.log('INFO', f'Take Profit: ${self.lucro_total:.2f}')
            self.running = False
            return False
        
        return True
    
    def _calculate_stake(self):
        if self.tipo_gestao == 'fixo':
            return self.valor_entrada
        elif self.tipo_gestao == 'martingale':
            if self.sequencia_loss > 0:
                multiplier = self.nivel_martingale ** self.sequencia_loss
                stake = self.valor_entrada * multiplier
                return min(stake, self.valor_entrada * 10)
            return self.valor_entrada
        elif self.tipo_gestao == 'soros':
            if self.sequencia_loss == 0 and self.lucro_total > 0:
                return self.valor_entrada + (self.lucro_total * 0.5)
            return self.valor_entrada
        return self.valor_entrada
    
    async def execute_trade(self, signal):
        try:
            stake = self._calculate_stake()
            self.valor_atual = stake
            
            contract_type = signal['signal']
            barrier = signal.get('barrier')
            
            self.log('ENTRADA', f'Tipo: {contract_type}')
            self.log('ENTRADA', f'Barrier: {barrier}')
            self.log('ENTRADA', f'Valor: ${stake:.2f}')
            self.log('ENTRADA', f'Ativo: {self.ativo}')
            
            # Compra contrato
            contract = await self.api.buy_contract(
                contract_type=contract_type,
                amount=stake,
                duration=5,
                symbol=self.ativo,
                duration_unit='t',
                barrier=barrier
            )
            
            if not contract:
                self.log('ERRO', 'Falha ao comprar contrato!')
                return
            
            contract_id = contract['contract_id']
            self.operacoes_hoje += 1
            
            self.log('ENTRADA', f'✅ Contrato #{contract_id} aberto!')
            
            # Aguarda resultado
            self.log('INFO', 'Aguardando resultado...')
            result = await self.api.check_contract_result(contract_id, timeout=45)
            
            if result:
                profit = result['profit']
                status = result['status']
                
                if status == 'WIN':
                    self.wins += 1
                    self.sequencia_loss = 0
                    self.log('RESULTADO', f'🎉 WIN! +${profit:.2f}')
                else:
                    self.losses += 1
                    self.sequencia_loss += 1
                    self.maior_sequencia_loss = max(self.maior_sequencia_loss, self.sequencia_loss)
                    self.log('RESULTADO', f'😔 LOSS! ${profit:.2f}')
                
                self.lucro_total += profit
                
                # Atualiza saldo
                balance_info = await self.api.get_balance()
                if balance_info:
                    self.saldo_atual = balance_info['balance']
                
                # Salva operação
                if self.save_operation_callback:
                    try:
                        self.save_operation_callback(
                            user_id=self.user_id,
                            tipo=contract_type,
                            ativo=self.ativo,
                            valor=stake,
                            resultado=status,
                            lucro=profit,
                            barrier=str(barrier),
                            confianca=signal.get('confidence', 0)
                        )
                    except Exception as e:
                        logger.error(f"Erro ao salvar operação: {e}")
                
                # Stats
                win_rate = (self.wins / (self.wins + self.losses)) * 100 if (self.wins + self.losses) > 0 else 0
                self.log('INFO', f'📊 {self.wins}W/{self.losses}L ({win_rate:.1f}%)')
                self.log('INFO', f'💰 Lucro total: ${self.lucro_total:.2f}')
                self.log('INFO', f'💵 Saldo: ${self.saldo_atual:.2f}')
            else:
                self.log('ERRO', 'Timeout ao aguardar resultado!')
                
        except Exception as e:
            self.log('ERRO', f'Erro no trade: {str(e)}')
            import traceback
            logger.error(traceback.format_exc())
    
    def stop(self):
        self.log('INFO', '⏹️ Parando robô...')
        self.running = False
    
    def pause(self):
        self.paused = True
        self.log('INFO', '⏸️ Robô pausado')
    
    def resume(self):
        self.paused = False
        self.log('INFO', '▶️ Robô retomado')
    
    def get_status(self):
        win_rate = (self.wins / (self.wins + self.losses)) * 100 if (self.wins + self.losses) > 0 else 0
        
        return {
            'running': self.running,
            'paused': self.paused,
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
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'tipo_gestao': self.tipo_gestao,
            'valor_entrada': self.valor_entrada,
            'valor_atual': self.valor_atual,
            'sequencia_loss': self.sequencia_loss,
            'maior_sequencia_loss': self.maior_sequencia_loss,
            'logs': list(self.logs)[-20:],
            'estrategia': 'TICKS_DIGIT',
            'strategy_stats': self.strategy.get_stats()
        }
