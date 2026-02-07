"""
DragonBot SaaS - Módulo de Trading
Versão: 2.0
"""

from .deriv_api import DerivAPI
from .strategy import Strategy
from .robot import TradingRobot

__all__ = ['DerivAPI', 'Strategy', 'TradingRobot']
__version__ = '2.0.0'
