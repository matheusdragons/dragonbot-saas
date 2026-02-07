"""
Estratégia de Probabilidade: Over/Under com análise de últimos dígitos
Para operações rápidas com ticks na Deriv
"""
from collections import Counter

class StrategyProbability:
    
    def __init__(self):
        # Configurações
        self.sample_size = 25
        self.threshold = 0.60
    
    
    def analyze(self, ticks):
        """
        Analisa últimos ticks e retorna sinal Over/Under
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
        
        if not last_digits:
            return None
        
        # Conta frequência de cada dígito (0-9)
        counter = Counter(last_digits)
        
        # Separa em Over (5-9) e Under (0-4)
        over_count = sum(counter[d] for d in range(5, 10))
        under_count = sum(counter[d] for d in range(0, 5))
        
        total = len(last_digits)
        over_percent = over_count / total
        under_percent = under_count / total
        
        
        # ESTRATÉGIA DE REVERSÃO
        
        # Se teve muitos OVER, aposta em UNDER (reversão)
        if over_percent >= self.threshold:
            return {
                'signal': 'DIGITUNDER',
                'barrier': '4',
                'price': recent_ticks[-1],
                'reason': f'Reversão: {over_percent:.0%} foram Over nos últimos {total} ticks'
            }
        
        # Se teve muitos UNDER, aposta em OVER (reversão)
        if under_percent >= self.threshold:
            return {
                'signal': 'DIGITOVER',
                'barrier': '5',
                'price': recent_ticks[-1],
                'reason': f'Reversão: {under_percent:.0%} foram Under nos últimos {total} ticks'
            }
        
        
        # ESTRATÉGIA DO DÍGITO RARO
        
        least_common = counter.most_common()[-1]
        least_digit = least_common[0]
        least_count = least_common[1]
        
        if least_count <= 2:
            if least_digit <= 4:
                return {
                    'signal': 'DIGITUNDER',
                    'barrier': str(least_digit),
                    'price': recent_ticks[-1],
                    'reason': f'Dígito {least_digit} raro: apareceu apenas {least_count}x'
                }
            else:
                return {
                    'signal': 'DIGITOVER',
                    'barrier': str(least_digit - 1),
                    'price': recent_ticks[-1],
                    'reason': f'Dígito {least_digit} raro: apareceu apenas {least_count}x'
                }
        
        # Sem sinal claro
        return None
