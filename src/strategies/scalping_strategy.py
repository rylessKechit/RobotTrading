"""
Stratégie de scalping hybride pour le trading de cryptomonnaies.
Combine l'analyse de tendance avec des indicateurs de momentum et volatilité.
"""

from typing import Dict, List, Optional
import pandas as pd
import numpy as np

from .base_strategy import BaseStrategy
from ..indicators.oscillators import RSI
from ..indicators.volatility import BollingerBands
from ..indicators.trend import MACD
from ..indicators.volume import VolumeNormalized
from ..utils.logger import get_logger

logger = get_logger(__name__)

class ScalpingStrategy(BaseStrategy):
    """
    Stratégie de scalping hybride pour le trading de cryptomonnaies.
    """
    
    def __init__(self, config, data_manager, exchange, risk_manager, event_system):
        """
        Initialise la stratégie de scalping.
        """
        super().__init__(config, data_manager, exchange, risk_manager, event_system)
        
        # Paramètres de la stratégie
        self.rsi_period = config.get("rsi_period", 14)
        self.rsi_oversold = config.get("rsi_oversold", 30)
        self.rsi_overbought = config.get("rsi_overbought", 70)
        
        self.bb_period = config.get("bb_period", 20)
        self.bb_std = config.get("bb_std", 2)
        
        self.macd_fast = config.get("macd_fast", 12)
        self.macd_slow = config.get("macd_slow", 26)
        self.macd_signal = config.get("macd_signal", 9)
        
        self.volume_period = config.get("volume_period", 20)
        self.volume_threshold = config.get("volume_threshold", 1.2)
        
        # Initialiser les indicateurs
        self.rsi = RSI(self.rsi_period)
        self.bollinger = BollingerBands(self.bb_period, self.bb_std)
        self.macd = MACD(self.macd_fast, self.macd_slow, self.macd_signal)
        self.volume_norm = VolumeNormalized(self.volume_period)
        
        logger.info(f"Scalping strategy initialized with parameters: RSI={self.rsi_period}, BB={self.bb_period},{self.bb_std}, MACD={self.macd_fast},{self.macd_slow},{self.macd_signal}")
    
    def execute(self):
        """
        Exécute la stratégie de trading.
        """
        for pair in self.pairs:
            # Récupérer les données de marché pour différents timeframes
            df_primary = self.data_manager.get_market_data(pair, self.timeframes["primary"])
            df_secondary = self.data_manager.get_market_data(pair, self.timeframes["secondary"])
            
            if df_primary is None or df_secondary is None:
                logger.warning(f"No data available for {pair}")
                continue
            
            # Déterminer la tendance à moyen terme
            trend = self._determine_trend(df_secondary)
            
            # Chercher des signaux d'entrée en fonction de la tendance
            if trend == "BULLISH":
                self._find_long_entry(pair, df_primary)
            elif trend == "BEARISH":
                self._find_short_entry(pair, df_primary)
    
    def _determine_trend(self, df):
        """
        Détermine la tendance actuelle sur le timeframe secondaire.
        """
        # Calculer les EMA pour déterminer la tendance
        df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
        df['ema100'] = df['close'].ewm(span=100, adjust=False).mean()
        
        last_close = df['close'].iloc[-1]
        last_ema50 = df['ema50'].iloc[-1]
        last_ema100 = df['ema100'].iloc[-1]
        
        if last_close > last_ema50 and last_ema50 > last_ema100:
            return "BULLISH"
        elif last_close < last_ema50 and last_ema50 < last_ema100:
            return "BEARISH"
        else:
            return "NEUTRAL"
    
    def _find_long_entry(self, pair, df):
        """
        Cherche des signaux d'entrée en position longue.
        """
        # Calculer les indicateurs
        df['rsi'] = self.rsi.calculate(df['close'])
        df['bb_upper'], df['bb_middle'], df['bb_lower'] = self.bollinger.calculate(df['close'])
        df['macd'], df['macd_signal'], df['macd_hist'] = self.macd.calculate(df['close'])
        df['volume_norm'] = self.volume_norm.calculate(df['volume'])
        
        # Conditions d'entrée LONG
        last_index = len(df) - 1
        
        entry_conditions = (
            (df['rsi'].iloc[-1] > self.rsi_oversold) and 
            (df['rsi'].iloc[-1] < 40) and
            (df['close'].iloc[-1] <= df['bb_lower'].iloc[-1]) and
            (df['macd_hist'].iloc[-1] > df['macd_hist'].iloc[-2]) and
            (df['volume_norm'].iloc[-1] > self.volume_threshold)
        )
        
        if entry_conditions:
            # Créer un signal d'entrée
            entry_price = df['close'].iloc[-1]
            
            # Calculer les niveaux de sortie
            stop_loss = entry_price * (1 - self.risk_params["stop_loss_pct"])
            take_profit1 = entry_price * (1 + self.risk_params["take_profit1_pct"])
            take_profit2 = entry_price * (1 + self.risk_params["take_profit2_pct"])
            
            # Calculer la taille de position
            position_size = self.risk_manager.calculate_position_size(
                pair, 
                entry_price, 
                stop_loss
            )
            
            # Créer l'ordre
            self._create_position(
                pair=pair,
                direction="LONG",
                entry_price=entry_price,
                position_size=position_size,
                stop_loss=stop_loss,
                take_profit1=take_profit1,
                take_profit2=take_profit2
            )
    
    def _find_short_entry(self, pair, df):
        """
        Cherche des signaux d'entrée en position courte.
        """
        # Implémentation similaire à _find_long_entry mais pour les positions courtes
        pass
    
    def _create_position(self, pair, direction, entry_price, position_size, stop_loss, take_profit1, take_profit2):
        """
        Crée une nouvelle position.
        """
        # Vérifier si les conditions de gestion des risques sont satisfaites
        if not self.risk_manager.can_open_position(pair, direction, position_size * entry_price):
            logger.info(f"Risk management prevented opening {direction} position on {pair}")
            return
        
        # Créer la position
        try:
            # Exécuter l'ordre d'entrée
            order_type = "MARKET"
            order_side = "BUY" if direction == "LONG" else "SELL"
            
            # Créer l'ordre d'entrée
            entry_order = self.exchange.create_order(
                symbol=pair,
                order_type=order_type,
                side=order_side,
                amount=position_size
            )
            
            # Enregistrer la position
            position = {
                "pair": pair,
                "direction": direction,
                "entry_price": entry_price,
                "entry_time": pd.Timestamp.now(),
                "position_size": position_size,
                "stop_loss": stop_loss,
                "take_profit1": take_profit1,
                "take_profit2": take_profit2,
                "entry_order_id": entry_order["id"]
            }
            
            # Placer les ordres de sortie
            self._place_exit_orders(position)
            
            # Ajouter la position à la liste des positions ouvertes
            position_id = f"{pair}_{pd.Timestamp.now().timestamp()}"
            self.positions[position_id] = position
            
            logger.info(f"Opened {direction} position on {pair} at {entry_price}")
            
        except Exception as e:
            logger.error(f"Error creating position: {str(e)}")
    
    def _place_exit_orders(self, position):
        """
        Place les ordres de sortie pour une position.
        """
        # Implémentation pour placer les ordres de sortie
        pass