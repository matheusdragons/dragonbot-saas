"""
DragonBot SaaS - Módulo de Trading
Versão: 2.0
"""

try:
    from .deriv_api import DerivAPI
    from .strategy import Strategy
    from .robot import TradingRobot
    __all__ = ['DerivAPI', 'Strategy', 'TradingRobot']
except ImportError as e:
    print(f"Aviso ao importar módulo bot: {e}")
    __all__ = []

__version__ = '2.0.0'
