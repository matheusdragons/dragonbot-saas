"""
DragonBot SaaS - Estratégia Simples: Differs do 7
Versão: 3.0

Regra: Se o último dígito for 7, aposta que o próximo NÃO será 7
Contrato: DIGITDIFF com barrier 7
Ativo: Volatility 10 Index (R_10)
"""

import logging

logger = logging.getLogger(__name__)


class Strategy:
    """
    Estratégia ultra simples: Differs do 7
    
    Quando o último dígito do preço for 7,
    aposta que o próximo dígito será diferente de 7.
    """
    
    def __init__(self):
        # Dígito alvo para monitorar
        self.digito_alvo = 7
        
        # Estatísticas
        self.total_signals = 0
        self.vezes_encontrou_7 = 0
        
        logger.info(f"📊 Estratégia: DIFFERS do {self.digito_alvo}")
        logger.info(f"📊 Quando encontrar {self.digito_alvo}, aposta DIGITDIFF")
    
    def extract_last_digit(self, price):
        """Extrai o último dígito de um preço."""
        try:
            # Converte para string e remove o ponto
            price_str = str(price).replace('.', '')
            # Pega o último caractere
            digit = int(price_str[-1])
            return digit
        except (ValueError, IndexError) as e:
            logger.error(f"Erro ao extrair dígito de {price}: {e}")
            return None
    
    def analyze(self, ticks):
        """
        Analisa os ticks e gera sinal se o último dígito for 7.
        
        Args:
            ticks: Lista de preços
            
        Returns:
            dict com sinal ou None
        """
        logger.info(f"🔍 Analisando {len(ticks) if ticks else 0} ticks...")
        
        if not ticks:
            logger.error("❌ Nenhum tick recebido!")
            return None
        
        # Pega o último tick
        ultimo_tick = ticks[-1]
        
        # Extrai o preço
        if isinstance(ultimo_tick, dict):
            ultimo_preco = ultimo_tick.get('quote') or ultimo_tick.get('price')
        else:
            ultimo_preco = ultimo_tick
        
        if not ultimo_preco:
            logger.error("❌ Não foi possível extrair o último preço!")
            return None
        
        ultimo_preco = float(ultimo_preco)
        
        # Extrai o último dígito
        ultimo_digito = self.extract_last_digit(ultimo_preco)
        
        if ultimo_digito is None:
            logger.error("❌ Não foi possível extrair o último dígito!")
            return None
        
        logger.info(f"📊 Último preço: {ultimo_preco}")
        logger.info(f"🔢 Último dígito: {ultimo_digito}")
        
        # Verifica se é o dígito alvo (7)
        if ultimo_digito == self.digito_alvo:
            self.vezes_encontrou_7 += 1
            self.total_signals += 1
            
            signal = {
                'signal': 'DIGITDIFF',
                'barrier': self.digito_alvo,  # 7
                'price': ultimo_preco,
                'last_digit': ultimo_digito,
                'confidence': 0.90,  # 90% chance de não ser 7 (1 em 10)
                'strategy': 'DIFFERS_7',
                'reason': f'Último dígito foi {self.digito_alvo}, apostando que o próximo será diferente'
            }
            
            logger.info(f"🎯 SINAL GERADO!")
            logger.info(f"   Tipo: DIGITDIFF")
            logger.info(f"   Barrier: {self.digito_alvo}")
            logger.info(f"   Aposta: Próximo dígito ≠ {self.digito_alvo}")
            
            return signal
        else:
            logger.info(f"⏳ Último dígito foi {ultimo_digito}, aguardando {self.digito_alvo}...")
            return None
    
    def get_stats(self):
        """Retorna estatísticas da estratégia."""
        return {
            'total_signals': self.total_signals,
            'vezes_encontrou_7': self.vezes_encontrou_7,
            'digito_alvo': self.digito_alvo,
            'estrategia': 'DIFFERS_7'
        }
    
    def reset_stats(self):
        """Reseta estatísticas."""
        self.total_signals = 0
        self.vezes_encontrou_7 = 0
