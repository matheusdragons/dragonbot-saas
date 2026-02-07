"""
DragonBot SaaS - Estratégia Over/Under com Ticks
Versão: 2.0 - Estratégia de Alta Frequência para Stress Test
"""

from collections import Counter
import logging

logger = logging.getLogger(__name__)


class Strategy:
    """
    Estratégia baseada em análise de últimos dígitos dos ticks.
    Gera sinais rápidos para DIGITOVER e DIGITUNDER.
    """
    
    def __init__(self):
        # Configurações da estratégia
        self.min_ticks = 20           # Mínimo de ticks para análise
        self.trend_threshold = 0.60   # 60% para considerar tendência
        self.rare_threshold = 0.05    # Dígito raro = menos de 5% de aparições
        
        # Contadores para estatísticas
        self.total_signals = 0
        self.signals_by_type = {'DIGITOVER': 0, 'DIGITUNDER': 0}
    
    def extract_last_digit(self, price):
        """
        Extrai o último dígito de um preço.
        Ex: 1234.567 → 7
        """
        try:
            # Converte para string e pega último caractere numérico
            price_str = str(price).replace('.', '')
            return int(price_str[-1])
        except (ValueError, IndexError):
            return None
    
    def analyze(self, ticks):
        """
        Analisa lista de ticks e retorna sinal de trading.
        
        Args:
            ticks: Lista de preços (floats) ou dicts com 'quote'
            
        Returns:
            dict com sinal ou None se não houver oportunidade
        """
        if not ticks or len(ticks) < self.min_ticks:
            logger.warning(f"Ticks insuficientes: {len(ticks) if ticks else 0}")
            return None
        
        # Extrai preços se vier como lista de dicts
        prices = []
        for tick in ticks:
            if isinstance(tick, dict):
                price = tick.get('quote') or tick.get('price')
            else:
                price = tick
            if price:
                prices.append(float(price))
        
        if len(prices) < self.min_ticks:
            return None
        
        # Extrai últimos dígitos
        digits = []
        for price in prices:
            digit = self.extract_last_digit(price)
            if digit is not None:
                digits.append(digit)
        
        if len(digits) < self.min_ticks:
            return None
        
        # Análise dos dígitos
        last_price = prices[-1]
        last_digit = digits[-1]
        
        # Conta frequência de cada dígito
        digit_counts = Counter(digits)
        total_digits = len(digits)
        
        # Calcula distribuição Over (5-9) vs Under (0-4)
        over_count = sum(digit_counts.get(d, 0) for d in [5, 6, 7, 8, 9])
        under_count = sum(digit_counts.get(d, 0) for d in [0, 1, 2, 3, 4])
        
        over_ratio = over_count / total_digits
        under_ratio = under_count / total_digits
        
        # Análise de pares vs ímpares
        even_count = sum(digit_counts.get(d, 0) for d in [0, 2, 4, 6, 8])
        odd_count = sum(digit_counts.get(d, 0) for d in [1, 3, 5, 7, 9])
        
        # Encontra dígito mais raro
        rarest_digit = min(digit_counts.keys(), key=lambda x: digit_counts[x])
        rarest_count = digit_counts[rarest_digit]
        rarest_ratio = rarest_count / total_digits
        
        # Encontra dígito mais frequente
        most_common_digit = max(digit_counts.keys(), key=lambda x: digit_counts[x])
        
        # Log de análise
        logger.info(f"📊 Análise: Over={over_ratio:.1%} Under={under_ratio:.1%} | "
                   f"Raro={rarest_digit}({rarest_ratio:.1%}) | Último={last_digit}")
        
        signal = None
        
        # ========== ESTRATÉGIA 1: REVERSÃO POR TENDÊNCIA ==========
        # Se muitos Over, aposta Under (reversão à média)
        if over_ratio >= self.trend_threshold:
            signal = {
                'signal': 'DIGITUNDER',
                'barrier': 4,  # Ganha se último dígito for 0,1,2,3,4
                'price': last_price,
                'confidence': over_ratio,
                'strategy': 'REVERSAO_TENDENCIA',
                'reason': f'Reversão: {over_ratio:.1%} dos ticks foram Over (5-9), esperando Under',
                'stats': {
                    'over_ratio': over_ratio,
                    'under_ratio': under_ratio,
                    'last_digit': last_digit,
                    'sample_size': total_digits
                }
            }
        
        # Se muitos Under, aposta Over (reversão à média)
        elif under_ratio >= self.trend_threshold:
            signal = {
                'signal': 'DIGITOVER',
                'barrier': 5,  # Ganha se último dígito for 5,6,7,8,9
                'price': last_price,
                'confidence': under_ratio,
                'strategy': 'REVERSAO_TENDENCIA',
                'reason': f'Reversão: {under_ratio:.1%} dos ticks foram Under (0-4), esperando Over',
                'stats': {
                    'over_ratio': over_ratio,
                    'under_ratio': under_ratio,
                    'last_digit': last_digit,
                    'sample_size': total_digits
                }
            }
        
        # ========== ESTRATÉGIA 2: PADRÃO PAR/ÍMPAR ==========
        elif even_count > odd_count * 1.5:  # 50% mais pares que ímpares
            # Muitos pares, aposta em ímpar (OVER com barrier 4 inclui mais ímpares)
            signal = {
                'signal': 'DIGITOVER',
                'barrier': 4,  # Ganha se >= 5 (inclui 5,7,9 ímpares)
                'price': last_price,
                'confidence': even_count / total_digits,
                'strategy': 'PAR_IMPAR',
                'reason': f'Padrão: {even_count} pares vs {odd_count} ímpares, esperando ímpares',
                'stats': {
                    'even_count': even_count,
                    'odd_count': odd_count,
                    'last_digit': last_digit,
                    'sample_size': total_digits
                }
            }
        
        elif odd_count > even_count * 1.5:  # 50% mais ímpares que pares
            signal = {
                'signal': 'DIGITUNDER',
                'barrier': 5,  # Ganha se <= 4 (inclui 0,2,4 pares)
                'price': last_price,
                'confidence': odd_count / total_digits,
                'strategy': 'PAR_IMPAR',
                'reason': f'Padrão: {odd_count} ímpares vs {even_count} pares, esperando pares',
                'stats': {
                    'even_count': even_count,
                    'odd_count': odd_count,
                    'last_digit': last_digit,
                    'sample_size': total_digits
                }
            }
        
        # ========== ESTRATÉGIA 3: DÍGITO SEQUENCIAL ==========
        # Se os últimos 3 dígitos são iguais, aposta em mudança
        elif len(digits) >= 3 and digits[-1] == digits[-2] == digits[-3]:
            repeated_digit = digits[-1]
            if repeated_digit >= 5:
                signal = {
                    'signal': 'DIGITUNDER',
                    'barrier': 4,
                    'price': last_price,
                    'confidence': 0.65,
                    'strategy': 'SEQUENCIA',
                    'reason': f'Sequência de 3x dígito {repeated_digit}, esperando mudança para Under',
                    'stats': {
                        'repeated_digit': repeated_digit,
                        'last_digit': last_digit,
                        'sample_size': total_digits
                    }
                }
            else:
                signal = {
                    'signal': 'DIGITOVER',
                    'barrier': 5,
                    'price': last_price,
                    'confidence': 0.65,
                    'strategy': 'SEQUENCIA',
                    'reason': f'Sequência de 3x dígito {repeated_digit}, esperando mudança para Over',
                    'stats': {
                        'repeated_digit': repeated_digit,
                        'last_digit': last_digit,
                        'sample_size': total_digits
                    }
                }
        
        # ========== ESTRATÉGIA 4: FALLBACK - SEMPRE GERA SINAL ==========
        # Para stress test, sempre gera um sinal baseado na distribuição atual
        else:
            if over_ratio > under_ratio:
                signal = {
                    'signal': 'DIGITUNDER',
                    'barrier': 4,
                    'price': last_price,
                    'confidence': 0.52,  # Confiança baixa
                    'strategy': 'FALLBACK',
                    'reason': f'Fallback: Over={over_ratio:.1%} > Under={under_ratio:.1%}',
                    'stats': {
                        'over_ratio': over_ratio,
                        'under_ratio': under_ratio,
                        'last_digit': last_digit,
                        'sample_size': total_digits
                    }
                }
            else:
                signal = {
                    'signal': 'DIGITOVER',
                    'barrier': 5,
                    'price': last_price,
                    'confidence': 0.52,
                    'strategy': 'FALLBACK',
                    'reason': f'Fallback: Under={under_ratio:.1%} >= Over={over_ratio:.1%}',
                    'stats': {
                        'over_ratio': over_ratio,
                        'under_ratio': under_ratio,
                        'last_digit': last_digit,
                        'sample_size': total_digits
                    }
                }
        
        # Atualiza estatísticas
        if signal:
            self.total_signals += 1
            self.signals_by_type[signal['signal']] += 1
            logger.info(f"🎯 SINAL: {signal['signal']} barrier={signal['barrier']} "
                       f"({signal['strategy']}) conf={signal['confidence']:.1%}")
        
        return signal
    
    def get_stats(self):
        """Retorna estatísticas da estratégia."""
        return {
            'total_signals': self.total_signals,
            'signals_by_type': self.signals_by_type,
            'trend_threshold': self.trend_threshold
        }
    
    def reset_stats(self):
        """Reseta estatísticas."""
        self.total_signals = 0
        self.signals_by_type = {'DIGITOVER': 0, 'DIGITUNDER': 0}
