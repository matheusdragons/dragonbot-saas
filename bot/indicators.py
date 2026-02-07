"""
Indicadores da estratégia: Bollinger + RSI + Value Chart
"""
import numpy as np

class Indicators:
    
    @staticmethod
    def bollinger_bands(closes, period=20, std_dev=2):
        """
        Calcula Bandas de Bollinger
        Retorna: (upper, middle, lower)
        """
        if len(closes) < period:
            return None, None, None
        
        closes = np.array(closes[-period:])
        
        middle = np.mean(closes)
        std = np.std(closes)
        
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        
        return upper, middle, lower
    
    
    @staticmethod
    def rsi(closes, period=14):
        """
        Calcula RSI (0-100)
        """
        if len(closes) < period + 1:
            return 50  # Retorna neutro se dados insuficientes
        
        closes = np.array(closes[-(period + 1):])
        deltas = np.diff(closes)
        
        gains = deltas.copy()
        losses = deltas.copy()
        
        gains[gains < 0] = 0
        losses[losses > 0] = 0
        losses = abs(losses)
        
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    
    @staticmethod
    def value_chart(closes, period=5):
        """
        Calcula Value Chart
        Retorna valor entre ~-12 e +12
        """
        if len(closes) < period:
            return 0
        
        closes = np.array(closes[-period:])
        
        sma = np.mean(closes)
        std = np.std(closes)
        
        if std == 0:
            return 0
        
        current_price = closes[-1]
        vc = (current_price - sma) / (std * 0.2)
        
        return vc
