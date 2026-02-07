"""
Estratégia: Confluência de 3 indicadores
"""
from bot.indicators import Indicators

class Strategy:
    
    def __init__(self):
        self.ind = Indicators()
        
        # Configurações
        self.bb_period = 20
        self.bb_std = 2
        self.rsi_period = 14
        self.rsi_overbought = 70
        self.rsi_oversold = 30
        self.vc_limit = 8
    
    
    def analyze(self, candles):
        """
        Analisa candles e retorna sinal
        Retorna: dict com sinal ou None
        """
        if len(candles) < 50:
            return None
        
        closes = [c['close'] for c in candles]
        current_price = closes[-1]
        
        # Calcula indicadores
        bb_upper, bb_middle, bb_lower = self.ind.bollinger_bands(closes, self.bb_period, self.bb_std)
        rsi = self.ind.rsi(closes, self.rsi_period)
        vc = self.ind.value_chart(closes)
        
        if bb_upper is None:
            return None
        
        
        # ========== SINAL DE PUT (Reversão para baixo) ==========
        cond_bb_put = current_price >= bb_upper
        cond_rsi_put = rsi >= self.rsi_overbought
        cond_vc_put = vc >= self.vc_limit
        
        if cond_bb_put and cond_rsi_put and cond_vc_put:
            return {
                'signal': 'PUT',
                'price': current_price,
                'bb_upper': bb_upper,
                'rsi': round(rsi, 2),
                'vc': round(vc, 2),
                'reason': f'BB: {current_price:.5f} >= {bb_upper:.5f} | RSI: {rsi:.1f} | VC: {vc:.1f}'
            }
        
        
        # ========== SINAL DE CALL (Reversão para cima) ==========
        cond_bb_call = current_price <= bb_lower
        cond_rsi_call = rsi <= self.rsi_oversold
        cond_vc_call = vc <= -self.vc_limit
        
        if cond_bb_call and cond_rsi_call and cond_vc_call:
            return {
                'signal': 'CALL',
                'price': current_price,
                'bb_lower': bb_lower,
                'rsi': round(rsi, 2),
                'vc': round(vc, 2),
                'reason': f'BB: {current_price:.5f} <= {bb_lower:.5f} | RSI: {rsi:.1f} | VC: {vc:.1f}'
            }
        
        
        return None
