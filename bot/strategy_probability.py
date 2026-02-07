"""
Estratégia de Probabilidade: Over/Under com análise de últimos dígitos
Alternativa rápida para testes - NÃO afeta a estratégia original
"""
from collections import Counter

class StrategyProbability:
    
    def __init__(self):
        # Configurações
        self.sample_size = 25        # Últimos 25 ticks para análise
        self.threshold = 0.60        # 60% de tendência para gerar sinal
    
    def analyze(self, ticks):
        """
        Analisa últimos ticks e retorna sinal Over/Under
        COMPATÍVEL com formato esperado pelo robot.py
        """
        if not ticks or len(ticks) < self.sample_size:
            return None
        
        # Pega últimos N ticks
        recent_ticks = ticks[-self.sample_size:]
        
        # Extrai último dígito de cada tick
        last_digits = []
        for tick in recent_ticks:
            tick_str = str(tick).replace('.', '').replace('-', '')
            if tick_str:
                last_digit = int(tick_str[-1])
                last_digits.append(last_digit)
        
        # Conta frequência
        counter = Counter(last_digits)
        
        # Separa em Over (5-9) e Under (0-4)
        over_count = sum(counter[d] for d in range(5, 10))
        under_count = sum(counter[d] for d in range(0, 5))
        
        total = len(last_digits)
        over_percent = over_count / total
        under_percent = under_count / total
        
        # REVERSÃO: Se muitos Over, aposta Under
        if over_percent >= self.threshold:
            return {
                'signal': 'DIGITUNDER',
                'barrier': '4',
                'price': recent_ticks[-1],
                'reason': f'Reversão: {over_percent:.0%} foram Over'
            }
        
        # REVERSÃO: Se muitos Under, aposta Over
        if under_percent >= self.threshold:
            return {
                'signal': 'DIGITOVER', 
                'barrier': '5',
                'price': recent_ticks[-1],
                'reason': f'Reversão: {under_percent:.0%} foram Under'
            }
        
        return None  # Sem sinal claro
