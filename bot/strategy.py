"""
DragonBot SaaS - Estratégia Simples: Dígito 7
Quando o último dígito for 7, aposta DIGITDIFF
"""

import logging

logger = logging.getLogger(__name__)


class Strategy:
    def __init__(self):
        self.total_signals = 0
        self.found_seven = 0
        logger.info("🎯 Estratégia do Dígito 7 iniciada!")
    
    def extract_last_digit(self, price):
        """Extrai o último dígito do preço."""
        try:
            # Converte para string e pega último caractere
            price_str = str(float(price))
            # Remove o ponto e pega o último dígito
            price_clean = price_str.replace('.', '')
            last_digit = int(price_clean[-1])
            return last_digit
        except Exception as e:
            logger.error(f"Erro ao extrair dígito: {e}")
            return None
    
    def analyze(self, ticks):
        """
        Analisa o último tick.
        Se o último dígito for 7, gera sinal DIGITDIFF.
        """
        if not ticks or len(ticks) == 0:
            logger.warning("Sem ticks para analisar")
            return None
        
        # Pega o último tick
        last_tick = ticks[-1]
        
        # Extrai o preço
        if isinstance(last_tick, dict):
            last_price = float(last_tick.get('quote', 0))
        else:
            last_price = float(last_tick)
        
        # Extrai o último dígito
        last_digit = self.extract_last_digit(last_price)
        
        logger.info(f"📊 Último preço: {last_price}")
        logger.info(f"🔢 Último dígito: {last_digit}")
        
        # REGRA SIMPLES: Se for 7, gera sinal
        if last_digit == 7:
            self.found_seven += 1
            self.total_signals += 1
            
            signal = {
                'signal': 'DIGITDIFF',
                'barrier': 7,
                'price': last_price,
                'confidence': 0.90,  # 90% de chance de não ser 7
                'reason': 'Último dígito foi 7, apostando que próximo será diferente'
            }
            
            logger.info("="*50)
            logger.info("🎯 SINAL GERADO!")
            logger.info(f"   Último dígito: 7")
            logger.info(f"   Ação: DIGITDIFF")
            logger.info(f"   Barrier: 7")
            logger.info("="*50)
            
            return signal
        else:
            logger.info(f"⏳ Último dígito foi {last_digit}, aguardando 7...")
            return None
    
    def get_stats(self):
        return {
            'total_signals': self.total_signals,
            'found_seven': self.found_seven
        }
