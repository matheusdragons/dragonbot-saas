"""
DragonBot SaaS - Estratégia Over/Under com Ticks
Versão: 2.1 - DEBUG MODE - Sempre gera sinal para teste
"""

from collections import Counter
import logging

logger = logging.getLogger(__name__)


class Strategy:
    """
    Estratégia baseada em análise de últimos dígitos dos ticks.
    MODO DEBUG: Sempre gera sinal para testar execução.
    """
    
    def __init__(self):
        self.min_ticks = 10  # Reduzido para teste
        self.trend_threshold = 0.55  # Reduzido para gerar mais sinais
        self.total_signals = 0
        self.signals_by_type = {'DIGITOVER': 0, 'DIGITUNDER': 0}
        
        logger.info("📊 Strategy inicializada - MODO DEBUG ATIVO")
    
    def extract_last_digit(self, price):
        """Extrai o último dígito de um preço."""
        try:
            price_str = str(price).replace('.', '')
            digit = int(price_str[-1])
            return digit
        except (ValueError, IndexError) as e:
            logger.error(f"Erro ao extrair dígito de {price}: {e}")
            return None
    
    def analyze(self, ticks):
        """
        Analisa lista de ticks e retorna sinal de trading.
        MODO DEBUG: Sempre retorna um sinal válido.
        """
        logger.info(f"🔍 Analisando {len(ticks) if ticks else 0} ticks...")
        
        if not ticks:
            logger.error("❌ Nenhum tick recebido!")
            return None
        
        if len(ticks) < self.min_ticks:
            logger.warning(f"⚠️ Poucos ticks: {len(ticks)}/{self.min_ticks}")
            # MODO DEBUG: Continua mesmo com poucos ticks
        
        # Extrai preços
        prices = []
        for tick in ticks:
            if isinstance(tick, dict):
                price = tick.get('quote') or tick.get('price')
            else:
                price = tick
            if price:
                prices.append(float(price))
        
        logger.info(f"📈 Preços extraídos: {len(prices)}")
        
        if not prices:
            logger.error("❌ Nenhum preço extraído!")
            return None
        
        # Extrai últimos dígitos
        digits = []
        for price in prices:
            digit = self.extract_last_digit(price)
            if digit is not None:
                digits.append(digit)
        
        logger.info(f"🔢 Dígitos extraídos: {digits[-10:]}...")  # Últimos 10
        
        if not digits:
            logger.error("❌ Nenhum dígito extraído!")
            return None
        
        # Análise
        last_price = prices[-1]
        last_digit = digits[-1]
        
        digit_counts = Counter(digits)
        total_digits = len(digits)
        
        over_count = sum(digit_counts.get(d, 0) for d in [5, 6, 7, 8, 9])
        under_count = sum(digit_counts.get(d, 0) for d in [0, 1, 2, 3, 4])
        
        over_ratio = over_count / total_digits if total_digits > 0 else 0.5
        under_ratio = under_count / total_digits if total_digits > 0 else 0.5
        
        logger.info(f"📊 Análise: Over={over_count}({over_ratio:.1%}) Under={under_count}({under_ratio:.1%})")
        logger.info(f"📊 Último dígito: {last_digit} | Último preço: {last_price}")
        
        # ========== DECISÃO DO SINAL ==========
        # MODO DEBUG: Sempre gera sinal baseado na análise
        
        if over_ratio > under_ratio:
            # Mais Over que Under -> Aposta UNDER (reversão)
            signal = {
                'signal': 'DIGITUNDER',
                'barrier': 4,  # Ganha se dígito for 0,1,2,3,4
                'price': last_price,
                'confidence': over_ratio,
                'strategy': 'REVERSAO',
                'reason': f'Over={over_ratio:.1%} > Under={under_ratio:.1%}, apostando UNDER',
                'stats': {
                    'over_ratio': over_ratio,
                    'under_ratio': under_ratio,
                    'last_digit': last_digit,
                    'sample_size': total_digits
                }
            }
        else:
            # Mais Under que Over -> Aposta OVER (reversão)
            signal = {
                'signal': 'DIGITOVER',
                'barrier': 5,  # Ganha se dígito for 5,6,7,8,9
                'price': last_price,
                'confidence': under_ratio,
                'strategy': 'REVERSAO',
                'reason': f'Under={under_ratio:.1%} >= Over={over_ratio:.1%}, apostando OVER',
                'stats': {
                    'over_ratio': over_ratio,
                    'under_ratio': under_ratio,
                    'last_digit': last_digit,
                    'sample_size': total_digits
                }
            }
        
        # Atualiza estatísticas
        self.total_signals += 1
        self.signals_by_type[signal['signal']] += 1
        
        logger.info(f"✅ SINAL GERADO: {signal['signal']} | Barrier: {signal['barrier']}")
        logger.info(f"📝 Razão: {signal['reason']}")
        
        return signal
    
    def get_stats(self):
        return {
            'total_signals': self.total_signals,
            'signals_by_type': self.signals_by_type,
            'trend_threshold': self.trend_threshold
        }
    
    def reset_stats(self):
        self.total_signals = 0
        self.signals_by_type = {'DIGITOVER': 0, 'DIGITUNDER': 0}
