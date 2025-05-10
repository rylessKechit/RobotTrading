"""
Module pour charger les données historiques nécessaires au backtesting.
"""

import os
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union
import ccxt
from datetime import datetime, timedelta

from ..utils.logger import get_logger

logger = get_logger(__name__)

class DataLoader:
    """
    Chargeur de données historiques pour le backtesting.
    """
    
    def __init__(self, config: Dict):
        """
        Initialise le chargeur de données.
        
        Args:
            config: Configuration du backtesting
        """
        self.config = config
        self.exchange_name = config.get("exchange", {}).get("name", "binance")
        self.data_dir = config.get("data_dir", "data/historical")
        self.timeframes = config.get("timeframes", {
            "primary": "5m",
            "secondary": "1h",
            "tertiary": "15m"
        })
        
        # Créer le répertoire de données s'il n'existe pas
        os.makedirs(self.data_dir, exist_ok=True)
    
    def load_data(self, pairs: List[str], start_date: pd.Timestamp, end_date: pd.Timestamp) -> Dict:
        """
        Charge les données historiques pour les paires et la période spécifiées.
        
        Args:
            pairs: Liste des paires de trading
            start_date: Date de début
            end_date: Date de fin
            
        Returns:
            Dictionnaire contenant les données historiques
        """
        market_data = {}
        
        for pair in pairs:
            market_data[pair] = {}
            
            for tf_name, timeframe in self.timeframes.items():
                logger.info(f"Loading {timeframe} data for {pair}")
                
                # Tenter de charger les données depuis un fichier local
                df = self._load_from_file(pair, timeframe, start_date, end_date)
                
                if df is None or df.empty:
                    # Si les données ne sont pas disponibles localement, les télécharger
                    df = self._download_data(pair, timeframe, start_date, end_date)
                    
                    if df is not None and not df.empty:
                        # Sauvegarder les données téléchargées pour une utilisation future
                        self._save_to_file(df, pair, timeframe)
                
                if df is not None and not df.empty:
                    market_data[pair][timeframe] = df
                    logger.info(f"Loaded {len(df)} {timeframe} data points for {pair}")
                else:
                    logger.warning(f"No data available for {pair} {timeframe}")
        
        return market_data
    
    def _load_from_file(self, pair: str, timeframe: str, start_date: pd.Timestamp, end_date: pd.Timestamp) -> Optional[pd.DataFrame]:
        """
        Charge les données depuis un fichier local.
        
        Args:
            pair: Paire de trading
            timeframe: Intervalle de temps
            start_date: Date de début
            end_date: Date de fin
            
        Returns:
            DataFrame contenant les données ou None si les données ne sont pas disponibles
        """
        # Construire le chemin du fichier
        pair_safe = pair.replace('/', '_')
        filename = f"{self.data_dir}/{pair_safe}_{timeframe}.csv"
        
        if not os.path.exists(filename):
            return None
        
        try:
            # Charger les données
            df = pd.read_csv(filename)
            
            # Convertir la colonne timestamp en index
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)
            
            # Filtrer les données pour la période spécifiée
            df = df[(df.index >= start_date) & (df.index <= end_date)]
            
            # Vérifier si nous avons suffisamment de données
            if len(df) < 10:
                logger.warning(f"Not enough data for {pair} {timeframe} in local file")
                return None
            
            return df
            
        except Exception as e:
            logger.error(f"Error loading data from file {filename}: {str(e)}")
            return None
    
    def _download_data(self, pair: str, timeframe: str, start_date: pd.Timestamp, end_date: pd.Timestamp) -> Optional[pd.DataFrame]:
        """
        Télécharge les données historiques depuis l'exchange.
        
        Args:
            pair: Paire de trading
            timeframe: Intervalle de temps
            start_date: Date de début
            end_date: Date de fin
            
        Returns:
            DataFrame contenant les données ou None si les données ne peuvent pas être téléchargées
        """
        try:
            # Initialiser l'exchange
            exchange_class = getattr(ccxt, self.exchange_name)
            exchange = exchange_class({
                'enableRateLimit': True  # Important pour éviter les limitations de l'API
            })
            
            logger.info(f"Downloading {timeframe} data for {pair} from {self.exchange_name}")
            
            # Récupérer les données par morceaux (en raison des limitations des API)
            all_ohlcv = []
            since = int(start_date.timestamp() * 1000)  # Convertir en millisecondes
            end_timestamp = int(end_date.timestamp() * 1000)
            
            # Limiter le nombre de bougies par requête
            limit = 1000
            
            # Télécharger les données par morceaux
            while since < end_timestamp:
                ohlcv = exchange.fetch_ohlcv(pair, timeframe, since, limit)
                
                if not ohlcv:
                    break
                
                all_ohlcv.extend(ohlcv)
                
                # Mettre à jour 'since' pour la prochaine requête
                since = ohlcv[-1][0] + 1
                
                # Pause pour éviter les limitations de l'API
                exchange.sleep(exchange.rateLimit)
            
            if not all_ohlcv:
                logger.warning(f"No data returned for {pair} {timeframe}")
                return None
            
            # Convertir les données en DataFrame
            df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # Convertir la colonne timestamp en index
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # Trier les données par timestamp
            df.sort_index(inplace=True)
            
            # Suppression des doublons éventuels
            df = df[~df.index.duplicated(keep='first')]
            
            # Filtrer les données pour la période spécifiée
            df = df[(df.index >= start_date) & (df.index <= end_date)]
            
            return df
            
        except Exception as e:
            logger.error(f"Error downloading data for {pair} {timeframe}: {str(e)}")
            return None
    
    def _save_to_file(self, df: pd.DataFrame, pair: str, timeframe: str) -> bool:
        """
        Sauvegarde les données dans un fichier local.
        
        Args:
            df: DataFrame contenant les données
            pair: Paire de trading
            timeframe: Intervalle de temps
            
        Returns:
            True si les données sont sauvegardées avec succès, False sinon
        """
        try:
            # Construire le chemin du fichier
            pair_safe = pair.replace('/', '_')
            filename = f"{self.data_dir}/{pair_safe}_{timeframe}.csv"
            
            # Sauvegarder les données
            df.to_csv(filename)
            
            logger.info(f"Saved {len(df)} {timeframe} data points for {pair} to {filename}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving data to file {filename}: {str(e)}")
            return False