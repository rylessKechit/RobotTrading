"""
Module pour les indicateurs techniques de type oscillateur.
"""

import numpy as np
import pandas as pd
from typing import Union, Tuple

class RSI:
    """
    Relative Strength Index (RSI).
    """
    
    def __init__(self, period: int = 14):
        """
        Initialise l'indicateur RSI.
        
        Args:
            period: Période du RSI
        """
        self.period = period
    
    def calculate(self, prices: Union[pd.Series, np.ndarray]) -> np.ndarray:
        """
        Calcule les valeurs du RSI.
        
        Args:
            prices: Série de prix
            
        Returns:
            Tableau des valeurs du RSI
        """
        if isinstance(prices, pd.Series):
            prices = prices.values
        
        # Calculer les variations de prix
        deltas = np.diff(prices)
        seed = deltas[:self.period+1]
        
        # Initialiser les gains et les pertes
        up = seed[seed >= 0].sum() / self.period
        down = -seed[seed < 0].sum() / self.period
        
        if down == 0:
            return np.ones_like(prices) * 100
        
        rs = up / down
        rsi = np.zeros_like(prices)
        rsi[:self.period] = 100. - 100. / (1. + rs)
        
        # Calculer le RSI pour les autres périodes
        for i in range(self.period, len(prices)):
            delta = deltas[i-1]
            
            if delta > 0:
                upval = delta
                downval = 0.
            else:
                upval = 0.
                downval = -delta
            
            up = (up * (self.period - 1) + upval) / self.period
            down = (down * (self.period - 1) + downval) / self.period
            
            rs = up / down if down != 0 else np.inf
            rsi[i] = 100. - 100. / (1. + rs)
        
        return rsi

class Stochastic:
    """
    Oscillateur stochastique.
    """
    
    def __init__(self, k_period: int = 14, d_period: int = 3, slowing: int = 3):
        """
        Initialise l'oscillateur stochastique.
        
        Args:
            k_period: Période du %K
            d_period: Période du %D
            slowing: Période de lissage
        """
        self.k_period = k_period
        self.d_period = d_period
        self.slowing = slowing
    
    def calculate(self, high: Union[pd.Series, np.ndarray], low: Union[pd.Series, np.ndarray], close: Union[pd.Series, np.ndarray]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Calcule les valeurs du stochastique.
        
        Args:
            high: Série des prix hauts
            low: Série des prix bas
            close: Série des prix de clôture
            
        Returns:
            Tuple contenant les valeurs de %K et %D
        """
        if isinstance(high, pd.Series):
            high = high.values
        if isinstance(low, pd.Series):
            low = low.values
        if isinstance(close, pd.Series):
            close = close.values
        
        # Calculer le %K
        k = np.zeros_like(close)
        
        for i in range(self.k_period - 1, len(close)):
            high_val = np.max(high[i - self.k_period + 1:i + 1])
            low_val = np.min(low[i - self.k_period + 1:i + 1])
            
            if high_val == low_val:
                k[i] = 50.0
            else:
                k[i] = 100.0 * (close[i] - low_val) / (high_val - low_val)
        
        # Calculer le %D
        d = np.zeros_like(close)
        for i in range(self.k_period + self.d_period - 2, len(close)):
            d[i] = np.mean(k[i - self.d_period + 1:i + 1])
        
        return k, d

class MACD:
    """
    Moving Average Convergence Divergence (MACD).
    """
    
    def __init__(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9):
        """
        Initialise l'indicateur MACD.
        
        Args:
            fast_period: Période de la moyenne mobile rapide
            slow_period: Période de la moyenne mobile lente
            signal_period: Période de la ligne de signal
        """
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
    
    def calculate(self, prices: Union[pd.Series, np.ndarray]) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Calcule les valeurs du MACD.
        
        Args:
            prices: Série de prix
            
        Returns:
            Tuple contenant les valeurs du MACD, de la ligne de signal et de l'histogramme
        """
        if isinstance(prices, pd.Series):
            prices = prices.values
        
        # Calculer les moyennes mobiles exponentielles
        ema_fast = self._ema(prices, self.fast_period)
        ema_slow = self._ema(prices, self.slow_period)
        
        # Calculer le MACD
        macd = ema_fast - ema_slow
        
        # Calculer la ligne de signal
        signal = self._ema(macd, self.signal_period)
        
        # Calculer l'histogramme
        histogram = macd - signal
        
        return macd, signal, histogram
    
    def _ema(self, prices: np.ndarray, period: int) -> np.ndarray:
        """
        Calcule la moyenne mobile exponentielle.
        
        Args:
            prices: Série de prix
            period: Période de la moyenne mobile
            
        Returns:
            Tableau des valeurs de la moyenne mobile exponentielle
        """
        ema = np.zeros_like(prices)
        ema[:period] = np.mean(prices[:period])
        
        alpha = 2.0 / (period + 1)
        for i in range(period, len(prices)):
            ema[i] = prices[i] * alpha + ema[i-1] * (1 - alpha)
        
        return ema