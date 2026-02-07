"""
DragonBot SaaS - Estratégia GARANTIDA de Execução
Versão: 5.0 - FORÇA EXECUÇÃO PARA TESTE
"""

import logging
from collections import Counter
import random

logger = logging.getLogger(__name__)


class Strategy:
    """
    Estratégia que SEMPRE gera sinal para garantir execução
    """
    
    def __init__(self):
        self.total_signals = 0
        self.last_signal = None
        self.signals_generated = []
        
        logger.info("🎯 ESTRATÉGIA ATIVA - MODO FORÇA EXECUÇÃO")
    
    def extract_last_digit(self, price):
        """Extrai o último dígito."""
        try:
            price_str = str(float(price)).replace('.', '')
            return int(price_str[-1])
        except:
            return random.randint(0, 9)
    
    def analyze(self, ticks):
        """
        SEMPRE retorna um sinal válido para teste
        """
        self.total_signals += 1
        
        logger.info(f"📊 ANÁLISE #{self.total_signals}")
        
        # Se não tem ticks, gera dados fake para teste
        if not ticks or len(ticks) < 5:
            logger.warning("⚠️ Sem ticks suficientes, gerando sinal padrão...")
            ticks = [{'quote': 1234.567 + i * 0.001} for i in range(10)]
        
        # Pega último preço
        if isinstance(ticks[-1], dict):
            last_price = float(ticks[-1].get('quote', 1234.567))
        else:
            last_price = float(ticks[-1])
        
        last_digit = self.extract_last_digit(last_price)
        
        logger.info(f"💹 Último preço: {last_price}")
        logger.info(f"🔢 Último dígito: {last_digit}")
        
        # ESTRATÉGIA SIMPLES: Alterna entre EVEN/ODD
        # EVEN = Par (0,2,4,6,8)
        # ODD = Ímpar (1,3,5,7,9)
        
        # Para garantir que funciona, usa DIGITEVEN/DIGITODD
        # que são suportados pela Deriv
        
        # Alterna sinais para não repetir
        if self.last_signal == 'DIGITEVEN':
            signal_type = 'DIGITODD'
        else:
            signal_type = 'DIGITEVEN'
        
        self.last_signal = signal_type
        
        signal = {
            'signal': signal_type,
            'barrier': None,  # EVEN/ODD não precisa barrier
            'price': last_price,
            'last_digit': last_digit,
            'confidence': 0.50,  # 50% sempre
            'strategy': 'EVEN_ODD',
            'reason': f'Apostando {signal_type} (teste de execução)'
        }
        
        logger.info(f"🎯 SINAL GERADO: {signal_type}")
        logger.info(f"📝 Total de sinais: {self.total_signals}")
        
        self.signals_generated.append(signal)
        
        return signal
    
    def get_stats(self):
        return {
            'total_signals': self.total_signals,
            'last_signal': self.last_signal,
            'signals_count': len(self.signals_generated)
        }
