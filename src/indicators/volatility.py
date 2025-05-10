"""
Module pour les indicateurs techniques de volatilité.
"""

import numpy as np
import pandas as pd
from typing import Union, Tuple, List

class BollingerBands:
    """
    Bandes de Bollinger.
    """
    
    def __init__(self, period: int = 20, num_std: float = 2.0):
        """
        Initialise les Bandes de Bollinger.
        
        Args:
            period: Période de la moyenne mobile
            num_std: Nombre d'écarts-types pour les bandes supérieure et inférieure
        """
        self.period = period
        self.num_std = num_std
    
    def calculate(self, prices: Union[pd.Series, np.ndarray]) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Calcule les valeurs des Bandes de Bollinger.
        
        Args:
            prices: Série de prix
            
        Returns:
            Tuple contenant les valeurs des bandes supérieure, moyenne et inférieure
        """
        if isinstance(prices, pd.Series):
            prices = prices.values
        
        # Calculer la moyenne mobile
        sma = np.zeros_like(prices)
        std = np.zeros_like(prices)
        
        for i in range(self.period - 1, len(prices)):
            sma[i] = np.mean(prices[i - self.period + 1:i + 1])
            std[i] = np.std(prices[i - self.period + 1:i + 1])
        
        # Calculer les bandes
        upper_band = sma + self.num_std * std
        lower_band = sma - self.num_std * std
        
        return upper_band, sma, lower_band

class ATR:
    """
    Average True Range (ATR).
    """
    
    def __init__(self, period: int = 14):
        """
        Initialise l'indicateur ATR.
        
        Args:
            period: Période de l'ATR
        """
        self.period = period
    
    def calculate(self, high: Union[pd.Series, np.ndarray], low: Union[pd.Series, np.ndarray], close: Union[pd.Series, np.ndarray]) -> np.ndarray:
        """
        Calcule les valeurs de l'ATR.
        
        Args:
            high: Série des prix hauts
            low: Série des prix bas
            close: Série des prix de clôture
            
        Returns:
            Tableau des valeurs de l'ATR
        """
        if isinstance(high, pd.Series):
            high = high.values
        if isinstance(low, pd.Series):
            low = low.values
        if isinstance(close, pd.Series):
            close = close.values
        
        # Calculer le True Range
        tr = np.zeros_like(close)
        tr[0] = high[0] - low[0]
        
        for i in range(1, len(close)):
            high_low = high[i] - low[i]
            high_close = abs(high[i] - close[i-1])
            low_close = abs(low[i] - close[i-1])
            
            tr[i] = max(high_low, high_close, low_close)
        
        # Calculer l'ATR
        atr = np.zeros_like(close)
        atr[:self.period] = np.mean(tr[:self.period])
        
        for i in range(self.period, len(close)):
            atr[i] = (atr[i-1] * (self.period - 1) + tr[i]) / self.period
        
        return atr

class KeltnerChannel:
    """
    Canal de Keltner.
    """
    
    def __init__(self, period: int = 20, atr_period: int = 10, atr_multiplier: float = 2.0):
        """
        Initialise le Canal de Keltner.
        
        Args:
            period: Période de la moyenne mobile
            atr_period: Période de l'ATR
            atr_multiplier: Multiplicateur de l'ATR
        """
        self.period = period
        self.atr_period = atr_period
        self.atr_multiplier = atr_multiplier
        self.atr = ATR(atr_period)
    
    def calculate(self, high: Union[pd.Series, np.ndarray], low: Union[pd.Series, np.ndarray], close: Union[pd.Series, np.ndarray]) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Calcule les valeurs du Canal de Keltner.
        
        Args:
            high: Série des prix hauts
            low: Série des prix bas
            close: Série des prix de clôture
            
        Returns:
            Tuple contenant les valeurs des bandes supérieure, moyenne et inférieure
        """
        if isinstance(high, pd.Series):
            high = high.values
        if isinstance(low, pd.Series):
            low = low.values
        if isinstance(close, pd.Series):
            close = close.values
        
        # Calculer l'EMA
        ema = np.zeros_like(close)
        ema[:self.period] = np.mean(close[:self.period])
        
        alpha = 2.0 / (self.period + 1)
        for i in range(self.period, len(close)):
            ema[i] = close[i] * alpha + ema[i-1] * (1 - alpha)
        
        # Calculer l'ATR
        atr_values = self.atr.calculate(high, low, close)
        
        # Calculer les bandes
        upper_band = ema + self.atr_multiplier * atr_values
        lower_band = ema - self.atr_multiplier * atr_values
        
        return upper_band, ema, lower_band