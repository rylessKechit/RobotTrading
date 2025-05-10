#!/usr/bin/env python3
"""
Script pour configurer les données de test pour le Robot Trader Crypto.
Ce script télécharge des données historiques publiques et met en place
un environnement de test qui ne nécessite pas d'API Binance.
"""

import os
import sys
import argparse
import logging
import requests
import pandas as pd
import json
from datetime import datetime, timedelta
import random

# Ajouter le répertoire parent au chemin de recherche des modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configurer la journalisation
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def download_historical_data(symbols, timeframes, start_date, end_date, data_dir):
    """
    Télécharge les données historiques depuis une source publique.
    
    Args:
        symbols: Liste des paires de trading
        timeframes: Liste des timeframes
        start_date: Date de début
        end_date: Date de fin
        data_dir: Répertoire pour sauvegarder les données
    """
    os.makedirs(data_dir, exist_ok=True)
    
    for symbol in symbols:
        logger.info(f"Downloading data for {symbol}...")
        
        # Remplacer le séparateur '/' par '_' pour le nom de fichier
        symbol_file = symbol.replace('/', '_')
        
        for timeframe in timeframes:
            logger.info(f"  Timeframe: {timeframe}")
            
            # Construire le chemin du fichier
            file_path = os.path.join(data_dir, f"{symbol_file}_{timeframe}.csv")
            
            try:
                # Essayer d'utiliser CryptoDataDownload API (gratuite et sans inscription)
                exchange = "binance"
                
                # Construire l'URL
                url = f"https://www.cryptodatadownload.com/cdd/Binance_{symbol_file}_{timeframe}.csv"
                
                # Télécharger les données
                response = requests.get(url)
                
                if response.status_code == 200:
                    # Sauvegarder les données brutes
                    with open(file_path, 'w') as f:
                        f.write(response.text)
                    
                    # Charger et traiter les données
                    df = pd.read_csv(file_path, skiprows=1)
                    
                    # Renommer les colonnes
                    df.columns = [c.lower() for c in df.columns]
                    
                    # Convertir la colonne de date en timestamp
                    df['timestamp'] = pd.to_datetime(df['date'])
                    
                    # Filtrer les données pour la période spécifiée
                    df = df[(df['timestamp'] >= pd.to_datetime(start_date)) & 
                           (df['timestamp'] <= pd.to_datetime(end_date))]
                    
                    # Sélectionner et réorganiser les colonnes
                    df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
                    
                    # Trier par timestamp
                    df.sort_values('timestamp', inplace=True)
                    
                    # Sauvegarder les données traitées
                    df.to_csv(file_path, index=False)
                    
                    logger.info(f"  Saved {len(df)} records to {file_path}")
                else:
                    # Si le téléchargement échoue, générer des données aléatoires
                    logger.warning(f"  Failed to download data. Generating random data...")
                    df = generate_random_data(symbol, timeframe, start_date, end_date)
                    df.to_csv(file_path, index=False)
                    logger.info(f"  Saved {len(df)} random records to {file_path}")
            
            except Exception as e:
                logger.error(f"  Error downloading data: {str(e)}")
                logger.warning(f"  Generating random data instead...")
                df = generate_random_data(symbol, timeframe, start_date, end_date)
                df.to_csv(file_path, index=False)
                logger.info(f"  Saved {len(df)} random records to {file_path}")

def generate_random_data(symbol, timeframe, start_date, end_date):
    """
    Génère des données aléatoires pour un symbole et un timeframe donnés.
    
    Args:
        symbol: Paire de trading
        timeframe: Intervalle de temps
        start_date: Date de début
        end_date: Date de fin
        
    Returns:
        DataFrame contenant les données générées
    """
    # Convertir les dates en datetime
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    
    # Déterminer l'intervalle en minutes
    if timeframe == '1m':
        interval_minutes = 1
    elif timeframe == '5m':
        interval_minutes = 5
    elif timeframe == '15m':
        interval_minutes = 15
    elif timeframe == '1h':
        interval_minutes = 60
    elif timeframe == '4h':
        interval_minutes = 240
    elif timeframe == '1d':
        interval_minutes = 1440
    else:
        interval_minutes = 1
    
    # Créer une liste de timestamps
    timestamps = []
    current = start
    while current <= end:
        timestamps.append(current)
        current += timedelta(minutes=interval_minutes)
    
    # Prix de base par symbole
    base_prices = {
        "BTC/USDT": 95000.0,
        "ETH/USDT": 4500.0,
        "SOL/USDT": 240.0,
        "LINK/BTC": 0.00055
    }
    
    # Récupérer le prix de base ou utiliser une valeur par défaut
    base_price = base_prices.get(symbol, 100.0)
    
    # Générer les données
    data = []
    price = base_price
    
    for timestamp in timestamps:
        # Générer des prix aléatoires
        daily_volatility = 0.02  # 2% de volatilité quotidienne
        timeframe_volatility = daily_volatility * (interval_minutes / 1440) ** 0.5
        
        price_change = price * random.normalvariate(0, timeframe_volatility)
        price += price_change
        
        # Générer les prix OHLCV
        open_price = price
        close_price = price * (1 + random.normalvariate(0, timeframe_volatility / 2))
        high_price = max(open_price, close_price) * (1 + abs(random.normalvariate(0, timeframe_volatility)))
        low_price = min(open_price, close_price) * (1 - abs(random.normalvariate(0, timeframe_volatility)))
        volume = abs(random.normalvariate(0, 1)) * base_price * 10
        
        data.append({
            'timestamp': timestamp,
            'open': max(0.00001, open_price),
            'high': max(0.00001, high_price),
            'low': max(0.00001, low_price),
            'close': max(0.00001, close_price),
            'volume': max(0.1, volume)
        })
        
        # Mettre à jour le prix pour la prochaine bougie
        price = close_price
    
    return pd.DataFrame(data)

def create_mock_config(config_path):
    """
    Crée un fichier de configuration pour utiliser l'exchange simulé.
    
    Args:
        config_path: Chemin où sauvegarder la configuration
    """
    config = {
        "exchange": {
            "name": "mock",
            "api_key": "",
            "api_secret": "",
            "data_dir": "data/historical",
            "initial_balance": {
                "USDT": 10000.0,
                "BTC": 0.1,
                "ETH": 1.0,
                "SOL": 10.0,
                "LINK": 50.0
            }
        },
        "trading_pairs": ["BTC/USDT", "ETH/USDT", "SOL/USDT", "LINK/BTC"],
        "mode": "paper_trading",
        "strategy": {
            "name": "scalping",
            "rsi_period": 14,
            "bb_period": 20,
            "bb_std": 2.0,
            "macd_fast": 12,
            "macd_slow": 26,
            "macd_signal": 9,
            "volume_period": 20
        },
        "risk_management": {
            "max_position_size_pct": 0.02,
            "max_total_exposure": 0.70,
            "max_consecutive_losses": 3,
            "max_drawdown_pct": 0.10,
            "default_stop_loss_pct": 0.015,
            "default_take_profit1_pct": 0.005,
            "default_take_profit2_pct": 0.01,
            "trailing_stop_pct": 0.003
        },
        "timeframes": {
            "primary": "5m",
            "secondary": "1h",
            "tertiary": "15m"
        },
        "use_mock_exchange": True
    }
    
    # Créer le répertoire si nécessaire
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    
    # Sauvegarder la configuration
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=4)
    
    logger.info(f"Created mock configuration file: {config_path}")

def create_backtest_config(config_path, start_date, end_date):
    """
    Crée un fichier de configuration pour le backtesting.
    
    Args:
        config_path: Chemin où sauvegarder la configuration
        start_date: Date de début
        end_date: Date de fin
    """
    config = {
        "exchange": {
            "name": "binance",
            "api_key": "",
            "api_secret": ""
        },
        "trading_pairs": ["BTC/USDT", "ETH/USDT", "SOL/USDT", "LINK/BTC"],
        "start_date": start_date,
        "end_date": end_date,
        "data_dir": "data/historical",
        "strategy_params": {
            "name": "scalping",
            "rsi_period": 14,
            "bb_period": 20,
            "bb_std": 2.0,
            "macd_fast": 12,
            "macd_slow": 26,
            "macd_signal": 9,
            "volume_period": 20
        },
        "risk_management": {
            "initial_capital": 10000,
            "max_position_size_pct": 0.02,
            "max_total_exposure": 0.70,
            "default_stop_loss_pct": 0.015,
            "default_take_profit1_pct": 0.005,
            "default_take_profit2_pct": 0.01,
            "trailing_stop_pct": 0.003,
            "max_consecutive_losses": 3,
            "max_drawdown_pct": 0.10
        },
        "timeframes": {
            "primary": "5m",
            "secondary": "1h",
            "tertiary": "15m"
        }
    }
    
    # Créer le répertoire si nécessaire
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    
    # Sauvegarder la configuration
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=4)
    
    logger.info(f"Created backtest configuration file: {config_path}")

def main():
    """
    Fonction principale.
    """
    # Analyser les arguments de la ligne de commande
    parser = argparse.ArgumentParser(description="Setup Mock Data for Robot Trader Crypto")
    parser.add_argument("--start-date", default=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"), help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", default=datetime.now().strftime("%Y-%m-%d"), help="End date (YYYY-MM-DD)")
    parser.add_argument("--data-dir", default="data/historical", help="Directory to save historical data")
    parser.add_argument("--config-dir", default="config", help="Directory to save configuration files")
    args = parser.parse_args()
    
    # Définir les paires et timeframes
    symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "LINK/BTC"]
    timeframes = ["1m", "5m", "15m", "1h", "4h", "1d"]
    
    # Créer les répertoires nécessaires
    os.makedirs(args.data_dir, exist_ok=True)
    os.makedirs(args.config_dir, exist_ok=True)
    
    # Télécharger les données historiques
    download_historical_data(symbols, timeframes, args.start_date, args.end_date, args.data_dir)
    
    # Créer les fichiers de configuration
    create_mock_config(os.path.join(args.config_dir, "config.json"))
    create_backtest_config(os.path.join(args.config_dir, "backtest_config.json"), args.start_date, args.end_date)
    
    logger.info("Setup completed successfully!")
    logger.info("You can now run the robot with: python run_bot.py --config config/config.json")
    logger.info("Or run a backtest with: python run_backtest.py --config config/backtest_config.json")

if __name__ == "__main__":
    main()