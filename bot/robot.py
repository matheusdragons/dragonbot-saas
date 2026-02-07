"""
DragonBot SaaS - Motor Principal do Robô
Versão: 2.0 - Suporte a estratégia de Ticks (Alta Frequência)
"""

import asyncio
import logging
from datetime import datetime
from collections import deque

from .deriv_api import DerivAPI
from .strategy import Strategy

logger = logging.getLogger(__name__)


class TradingRobot:
    """
    Robô de trading automatizado.
    Versão 2.0: Estratégia de Ticks com DIGITOVER/DIGITUNDER.
    """
    
    def __init__(self, user_config):
        """
        Inicializa o robô com configurações do usuário.
        
        Args:
            user_config: dict com configurações do usuário
        """
        self.config = user_config
        self.user_id = user_config.get('user_id')
        
        # Configurações de trading
        self.deriv_token = user_config.get('deriv_token')
        self.deriv_app_id = user_config.get('deriv_app_id', '1089')
        self.valor_entrada = float(user_config.get('valor_entrada', 1.0))
        self.stop_loss = float(user_config.get('stop_loss', 50.0))
        self.take_profit = float(user_config.get('take_profit', 100.0))
        self.max_operacoes = int(user_config.get('max_operacoes_dia', 50))
        self.ativo = user_config.get('ativo', 'R_75')
        
        # Gestão de banca
        self.tipo_gestao = user_config.get('tipo_gestao', 'fixo')
        self.nivel_martingale = float(user_config.get('nivel_martingale', 2.0))
        
        # Componentes
        self.api = DerivAPI(app_id=self.deriv_app_id, token=self.deriv_token)
        self.strategy = Strategy()
        
        # Estado
        self.running = False
        self.paused = False
        self.saldo_inicial = 0
        self.saldo_atual = 0
        
        # Contadores
        self.operacoes_hoje = 0
        self.wins = 0
        self.losses = 0
        self.lucro_total = 0
        self.sequencia_loss = 0
        self.maior_sequencia_loss = 0
        
        # Valor atual (para martingale)
        self.valor_atual = self.valor_entrada
        
        # Logs em memória (últimos 100)
        self.logs = deque(maxlen=100)
        
        # Callback para salvar operações (injetado pelo app.py)
        self.save_operation_callback = None
        self.save_log_callback = None
    
    def log(self, tipo, mensagem):
        """
        Registra log do robô.
        
        Args:
            tipo: INFO, SINAL, ENTRADA, RESULTADO, ERRO
            mensagem: Texto do log
        """
        timestamp = datetime.now()
        log_entry = {
            'tipo': tipo,
            'mensagem': mensagem,
            'data': timestamp.isoformat(),
            'timestamp': timestamp
        }
        
        self.logs.append(log_entry)
        
        # Log no console também
        log_func = logger.error if tipo == 'ERRO' else logger.info
        log_func(f"[{tipo}] {mensagem}")
        
        # Callback para salvar no banco
        if self.save_log_callback:
            try:
                self.save_log_callback(self.user_id, tipo, mensagem)
            except Exception as e:
                logger.error(f"Erro ao salvar log: {e}")
    
    async def start(self):
        """Inicia o robô de trading."""
        self.log('INFO', '🚀 Iniciando DragonBot v2.0...')
        
        try:
            # Conecta à API
            connected = await self.api.connect()
            if not connected:
                self.log('ERRO', '❌ Falha ao conectar na Deriv API')
                return False
            
            # Verifica autorização
            if not self.api.is_authorized():
                self.log('ERRO', '❌ Falha na autorização - verifique seu token')
                return False
            
            # Busca saldo inicial
            balance_info = await self.api.get_balance()
            if balance_info:
                self.saldo_inicial = balance_info['balance']
                self.saldo_atual = self.saldo_inicial
                self.log('INFO', f'💰 Saldo inicial: ${self.saldo_inicial:.2f}')
            
            # Inicia loop principal
            self.running = True
            self.log('INFO', f'✅ Robô iniciado! Ativo: {self.ativo} | Entrada: ${self.valor_entrada}')
            self.log('INFO', f'📊 Stop Loss: ${self.stop_loss} | Take Profit: ${self.take_profit}')
            self.log('INFO', f'🎯 Estratégia: Ticks (DIGITOVER/DIGITUNDER)')
            
            await self.run_loop()
            return True
            
        except Exception as e:
            self.log('ERRO', f'❌ Erro ao iniciar: {str(e)}')
            return False
    
    async def run_loop(self):
        """Loop principal de trading."""
        self.log('INFO', '🔄 Iniciando loop de análise...')
        
        while self.running:
            try:
                # Verifica se atingiu limites
                if not self._check_limits():
                    break
                
                # Pausa se necessário
                if self.paused:
                    await asyncio.sleep(5)
                    continue
                
                # Busca ticks recentes
                ticks = await self.api.get_ticks(symbol=self.ativo, count=30)
                
                if not ticks:
                    self.log('ERRO', '❌ Falha ao buscar ticks')
                    await asyncio.sleep(10)
                    continue
                
                # Analisa estratégia
                signal = self.strategy.analyze(ticks)
                
                if signal:
                    self.log('SINAL', f"🎯 {signal['signal']} | Barrier: {signal['barrier']} | "
                                      f"Confiança: {signal['confidence']:.1%}")
                    self.log('SINAL', f"📝 Razão: {signal['reason']}")
                    
                    # Executa trade
                    await self.execute_trade(signal)
                else:
                    self.log('INFO', '⏳ Aguardando oportunidade...')
                
                # Intervalo entre análises (10 segundos para stress test)
                await asyncio.sleep(10)
                
            except asyncio.CancelledError:
                self.log('INFO', '⏹️ Loop cancelado')
                break
            except Exception as e:
                self.log('ERRO', f'❌ Erro no loop: {str(e)}')
                await asyncio.sleep(10)
        
        self.log('INFO', '🛑 Loop de trading finalizado')
        await self.api.disconnect()
    
    def _check_limits(self):
        """Verifica se atingiu limites de operação."""
        # Verifica máximo de operações
        if self.operacoes_hoje >= self.max_operacoes:
            self.log('INFO', f'🛑 Máximo de operações atingido: {self.max_operacoes}')
            self.running = False
            return False
        
        # Verifica stop loss
        if self.lucro_total <= -self.stop_loss:
            self.log('INFO', f'🛑 Stop Loss atingido: ${self.lucro_total:.2f}')
            self.running = False
            return False
        
        # Verifica take profit
        if self.lucro_total >= self.take_profit:
            self.log('INFO', f'🎉 Take Profit atingido: ${self.lucro_total:.2f}')
            self.running = False
            return False
        
        return True
    
    def _calculate_stake(self):
        """Calcula valor da entrada baseado na gestão de banca."""
        if self.tipo_gestao == 'fixo':
            return self.valor_entrada
        
        elif self.tipo_gestao == 'martingale':
            if self.sequencia_loss > 0:
                # Dobra após cada loss
                multiplier = self.nivel_martingale ** self.sequencia_loss
                stake = self.valor_entrada * multiplier
                # Limita a 10x o valor inicial
                return min(stake, self.valor_entrada * 10)
            return self.valor_entrada
        
        elif self.tipo_gestao == 'soros':
            if self.sequencia_loss == 0 and self.lucro_total > 0:
                # Aumenta após win
                return self.valor_entrada + (self.lucro_total * 0.5)
            return self.valor_entrada
        
        return self.valor_entrada
    
    async def execute_trade(self, signal):
        """
        Executa uma operação de trading.
        
        Args:
            signal: Dict com dados do sinal
        """
        try:
            # Calcula valor da entrada
            stake = self._calculate_stake()
            self.valor_atual = stake
            
            contract_type = signal['signal']  # DIGITOVER ou DIGITUNDER
            barrier = signal.get('barrier')
            
            self.log('ENTRADA', f'📈 Executando: {contract_type} | Barrier: {barrier} | '
                               f'Valor: ${stake:.2f}')
            
            # Compra o contrato
            contract = await self.api.buy_contract(
                contract_type=contract_type,
                amount=stake,
                duration=5,  # 5 ticks
                symbol=self.ativo,
                duration_unit='t',  # ticks
                barrier=barrier
            )
            
            if not contract:
                self.log('ERRO', '❌ Falha ao comprar contrato')
                return
            
            contract_id = contract['contract_id']
            self.operacoes_hoje += 1
            
            self.log('ENTRADA', f'✅ Contrato aberto: #{contract_id}')
            
            # Aguarda resultado (máximo 30 segundos para 5 ticks)
            result = await self.api.check_contract_result(contract_id, timeout=30)
            
            if result:
                profit = result['profit']
                status = result['status']
                
                if status == 'WIN':
                    self.wins += 1
                    self.sequencia_loss = 0
                    self.log('RESULTADO', f'🎉 WIN! Lucro: +${profit:.2f}')
                else:
                    self.losses += 1
                    self.sequencia_loss += 1
                    self.maior_sequencia_loss = max(self.maior_sequencia_loss, self.sequencia_loss)
                    self.log('RESULTADO', f'😔 LOSS! Prejuízo: ${profit:.2f}')
                
                self.lucro_total += profit
                
                # Atualiza saldo
                balance_info = await self.api.get_balance()
                if balance_info:
                    self.saldo_atual = balance_info['balance']
                
                # Salva operação no banco
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
                
                # Log de estatísticas
                win_rate = (self.wins / (self.wins + self.losses)) * 100 if (self.wins + self.losses) > 0 else 0
                self.log('INFO', f'📊 Stats: {self.wins}W/{self.losses}L ({win_rate:.1f}%) | '
                                f'Lucro: ${self.lucro_total:.2f}')
            else:
                self.log('ERRO', '❌ Não foi possível obter resultado do contrato')
                
        except Exception as e:
            self.log('ERRO', f'❌ Erro ao executar trade: {str(e)}')
    
    def stop(self):
        """Para o robô."""
        self.log('INFO', '⏹️ Parando robô...')
        self.running = False
    
    def pause(self):
        """Pausa o robô."""
        self.paused = True
        self.log('INFO', '⏸️ Robô pausado')
    
    def resume(self):
        """Retoma o robô."""
        self.paused = False
        self.log('INFO', '▶️ Robô retomado')
    
    def get_status(self):
        """Retorna status atual do robô."""
        win_rate = (self.wins / (self.wins + self.losses)) * 100 if (self.wins + self.losses) > 0 else 0
        
        return {
            'running': self.running,
            'paused': self.paused,
            'user_id': self.user_id,
            'ativo': self.ativo,
            
            # Saldo
            'saldo_inicial': self.saldo_inicial,
            'saldo_atual': self.saldo_atual,
            
            # Operações
            'operacoes_hoje': self.operacoes_hoje,
            'max_operacoes': self.max_operacoes,
            'wins': self.wins,
            'losses': self.losses,
            'win_rate': win_rate,
            
            # Lucro
            'lucro_total': self.lucro_total,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            
            # Gestão
            'tipo_gestao': self.tipo_gestao,
            'valor_entrada': self.valor_entrada,
            'valor_atual': self.valor_atual,
            'sequencia_loss': self.sequencia_loss,
            'maior_sequencia_loss': self.maior_sequencia_loss,
            
            # Logs (últimos 20)
            'logs': list(self.logs)[-20:],
            
            # Estratégia
            'estrategia': 'TICKS_DIGIT',
            'strategy_stats': self.strategy.get_stats()
        }
