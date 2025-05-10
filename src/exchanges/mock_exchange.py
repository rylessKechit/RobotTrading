"""
Exchange simulé pour tester le robot sans API réelle.
"""

import os
import time
import random
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union

from .exchange_base import ExchangeBase
from ..utils.logger import get_logger

logger = get_logger(__name__)

class MockExchange(ExchangeBase):
    """
    Exchange simulé pour tester le robot sans API réelle.
    """
    
    def __init__(self, config: Dict):
        """
        Initialise l'exchange simulé.
        
        Args:
            config: Configuration de l'exchange
        """
        super().__init__(config)
        
        self.data_dir = config.get("data_dir", "data/historical")
        self.balance = config.get("initial_balance", {
            "USDT": 10000.0,
            "BTC": 0.1,
            "ETH": 1.0,
            "SOL": 10.0,
            "LINK": 50.0
        })
        
        self.markets = self._create_markets()
        self.orders = {}
        self.order_id_counter = 0
        
        # Charger les données historiques pour simuler les prix
        self._load_historical_data()
        
        # Index temporel pour simuler l'avancement du temps
        self.current_time_idx = 0
        
        logger.info("Mock exchange initialized")
    
    def connect(self) -> bool:
        """
        Établit la connexion avec l'exchange (simulé).
        
        Returns:
            True (toujours réussi pour un exchange simulé)
        """
        return True
    
    def get_balance(self) -> Dict:
        """
        Récupère le solde du compte simulé.
        
        Returns:
            Dictionnaire contenant les soldes par devise
        """
        return {
            "free": self.balance.copy(),
            "used": {k: 0.0 for k in self.balance},
            "total": self.balance.copy()
        }
    
    def get_ticker(self, symbol: str) -> Dict:
        """
        Récupère le ticker pour un symbole donné.
        
        Args:
            symbol: Symbole de la paire (ex: "BTC/USDT")
            
        Returns:
            Dictionnaire contenant les informations du ticker
        """
        try:
            # Récupérer les données du marché
            current_time, ohlcv = self._get_current_ohlcv(symbol)
            
            if ohlcv is None:
                # Si pas de données disponibles, générer des données aléatoires
                return self._generate_random_ticker(symbol)
            
            # Créer le ticker à partir des données OHLCV
            ticker = {
                "symbol": symbol,
                "timestamp": current_time.timestamp() * 1000,
                "datetime": current_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "high": ohlcv["high"],
                "low": ohlcv["low"],
                "bid": ohlcv["close"] * 0.999,
                "ask": ohlcv["close"] * 1.001,
                "last": ohlcv["close"],
                "close": ohlcv["close"],
                "previousClose": ohlcv["open"],
                "change": ohlcv["close"] - ohlcv["open"],
                "percentage": (ohlcv["close"] - ohlcv["open"]) / ohlcv["open"] * 100 if ohlcv["open"] > 0 else 0,
                "average": (ohlcv["high"] + ohlcv["low"]) / 2,
                "baseVolume": ohlcv["volume"],
                "quoteVolume": ohlcv["volume"] * ohlcv["close"],
                "info": {}
            }
            
            return ticker
            
        except Exception as e:
            logger.error(f"Error getting ticker for {symbol}: {str(e)}")
            return self._generate_random_ticker(symbol)
    
    def get_ohlcv(self, symbol: str, timeframe: str, limit: int = 100, since: Optional[int] = None) -> List:
        """
        Récupère les données OHLCV pour un symbole et un timeframe donnés.
        
        Args:
            symbol: Symbole de la paire (ex: "BTC/USDT")
            timeframe: Intervalle de temps (ex: "1m", "5m", "1h")
            limit: Nombre de bougies à récupérer
            since: Timestamp en millisecondes à partir duquel récupérer les données
            
        Returns:
            Liste de listes contenant les données OHLCV
        """
        try:
            # Vérifier si les données sont disponibles
            if symbol not in self.historical_data or timeframe not in self.historical_data[symbol]:
                # Si pas de données disponibles, générer des données aléatoires
                return self._generate_random_ohlcv(limit)
            
            # Récupérer les données
            df = self.historical_data[symbol][timeframe]
            
            # Filtrer par timestamp si spécifié
            if since is not None:
                since_date = pd.to_datetime(since, unit='ms')
                df = df[df.index >= since_date]
            
            # Limiter le nombre de résultats
            df = df.iloc[-limit:]
            
            # Convertir en liste de listes
            ohlcv = []
            for idx, row in df.iterrows():
                timestamp = int(idx.timestamp() * 1000)
                ohlcv.append([
                    timestamp,
                    row['open'],
                    row['high'],
                    row['low'],
                    row['close'],
                    row['volume']
                ])
            
            return ohlcv
            
        except Exception as e:
            logger.error(f"Error getting OHLCV for {symbol} {timeframe}: {str(e)}")
            return self._generate_random_ohlcv(limit)
    
    def create_order(self, symbol: str, order_type: str, side: str, amount: float, price: Optional[float] = None) -> Dict:
        """
        Crée un ordre sur l'exchange simulé.
        
        Args:
            symbol: Symbole de la paire (ex: "BTC/USDT")
            order_type: Type d'ordre ("MARKET", "LIMIT", etc.)
            side: Côté de l'ordre ("BUY", "SELL")
            amount: Quantité à acheter/vendre
            price: Prix pour les ordres limites (optionnel)
            
        Returns:
            Dictionnaire contenant les informations de l'ordre créé
        """
        try:
            # Récupérer le prix actuel si nécessaire
            if price is None or order_type.upper() == "MARKET":
                current_price = self.get_ticker(symbol)["last"]
            else:
                current_price = price
            
            # Calculer le coût total
            cost = amount * current_price
            
            # Extraire les devises
            base_currency, quote_currency = symbol.split('/')
            
            # Vérifier le solde
            if side.upper() == "BUY":
                if self.balance[quote_currency] < cost:
                    raise Exception(f"Insufficient balance: {self.balance[quote_currency]} {quote_currency} < {cost} {quote_currency}")
                
                # Mettre à jour le solde
                self.balance[quote_currency] -= cost
                self.balance[base_currency] += amount
                
            elif side.upper() == "SELL":
                if self.balance[base_currency] < amount:
                    raise Exception(f"Insufficient balance: {self.balance[base_currency]} {base_currency} < {amount} {base_currency}")
                
                # Mettre à jour le solde
                self.balance[base_currency] -= amount
                self.balance[quote_currency] += cost
            
            # Créer l'ordre
            self.order_id_counter += 1
            order_id = str(self.order_id_counter)
            
            order = {
                "id": order_id,
                "symbol": symbol,
                "type": order_type.upper(),
                "side": side.upper(),
                "amount": amount,
                "price": current_price,
                "cost": cost,
                "filled": amount,
                "remaining": 0,
                "status": "closed",
                "timestamp": int(time.time() * 1000),
                "datetime": pd.Timestamp.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "fee": {
                    "currency": quote_currency if side.upper() == "BUY" else base_currency,
                    "cost": cost * 0.001,  # Frais simulés de 0.1%
                    "rate": 0.001
                }
            }
            
            # Stocker l'ordre
            self.orders[order_id] = order
            
            logger.info(f"Created {side} order for {amount} {symbol} at {current_price}")
            
            return order
            
        except Exception as e:
            logger.error(f"Error creating order: {str(e)}")
            raise
    
    def cancel_order(self, order_id: str, symbol: str) -> bool:
        """
        Annule un ordre sur l'exchange simulé.
        
        Args:
            order_id: Identifiant de l'ordre
            symbol: Symbole de la paire
            
        Returns:
            True si l'ordre est annulé avec succès, False sinon
        """
        try:
            if order_id in self.orders:
                order = self.orders[order_id]
                
                if order["status"] in ["open", "partial"]:
                    order["status"] = "canceled"
                    
                    # Rembourser le solde si nécessaire
                    if order["side"] == "BUY":
                        quote_currency = order["symbol"].split('/')[1]
                        self.balance[quote_currency] += order["remaining"] * order["price"]
                    
                    elif order["side"] == "SELL":
                        base_currency = order["symbol"].split('/')[0]
                        self.balance[base_currency] += order["remaining"]
                    
                    logger.info(f"Canceled order {order_id}")
                    return True
                else:
                    logger.warning(f"Order {order_id} is already {order['status']}")
                    return False
            else:
                logger.warning(f"Order {order_id} not found")
                return False
                
        except Exception as e:
            logger.error(f"Error canceling order: {str(e)}")
            return False
    
    def get_order(self, order_id: str, symbol: str) -> Dict:
        """
        Récupère les informations d'un ordre.
        
        Args:
            order_id: Identifiant de l'ordre
            symbol: Symbole de la paire
            
        Returns:
            Dictionnaire contenant les informations de l'ordre
        """
        if order_id in self.orders:
            return self.orders[order_id]
        else:
            raise Exception(f"Order {order_id} not found")
    
    def get_open_orders(self, symbol: Optional[str] = None) -> List:
        """
        Récupère les ordres ouverts.
        
        Args:
            symbol: Symbole de la paire (optionnel)
            
        Returns:
            Liste des ordres ouverts
        """
        open_orders = []
        
        for order in self.orders.values():
            if order["status"] in ["open", "partial"]:
                if symbol is None or order["symbol"] == symbol:
                    open_orders.append(order)
        
        return open_orders
    
    def _create_markets(self) -> Dict:
        """
        Crée la liste des marchés disponibles.
        
        Returns:
            Dictionnaire contenant les informations des marchés
        """
        return {
            "BTC/USDT": {
                "id": "BTCUSDT",
                "symbol": "BTC/USDT",
                "base": "BTC",
                "quote": "USDT",
                "baseId": "BTC",
                "quoteId": "USDT",
                "active": True,
                "precision": {
                    "amount": 6,
                    "price": 2
                },
                "limits": {
                    "amount": {
                        "min": 0.000001,
                        "max": 1000
                    },
                    "price": {
                        "min": 1,
                        "max": 1000000
                    },
                    "cost": {
                        "min": 10
                    }
                }
            },
            "ETH/USDT": {
                "id": "ETHUSDT",
                "symbol": "ETH/USDT",
                "base": "ETH",
                "quote": "USDT",
                "baseId": "ETH",
                "quoteId": "USDT",
                "active": True,
                "precision": {
                    "amount": 5,
                    "price": 2
                },
                "limits": {
                    "amount": {
                        "min": 0.00001,
                        "max": 10000
                    },
                    "price": {
                        "min": 1,
                        "max": 100000
                    },
                    "cost": {
                        "min": 10
                    }
                }
            },
            "SOL/USDT": {
                "id": "SOLUSDT",
                "symbol": "SOL/USDT",
                "base": "SOL",
                "quote": "USDT",
                "baseId": "SOL",
                "quoteId": "USDT",
                "active": True,
                "precision": {
                    "amount": 3,
                    "price": 3
                },
                "limits": {
                    "amount": {
                        "min": 0.001,
                        "max": 100000
                    },
                    "price": {
                        "min": 0.001,
                        "max": 10000
                    },
                    "cost": {
                        "min": 10
                    }
                }
            },
            "LINK/BTC": {
                "id": "LINKBTC",
                "symbol": "LINK/BTC",
                "base": "LINK",
                "quote": "BTC",
                "baseId": "LINK",
                "quoteId": "BTC",
                "active": True,
                "precision": {
                    "amount": 2,
                    "price": 8
                },
                "limits": {
                    "amount": {
                        "min": 0.01,
                        "max": 100000
                    },
                    "price": {
                        "min": 0.00000001,
                        "max": 1
                    },
                    "cost": {
                        "min": 0.0001
                    }
                }
            }
        }
    
    def _load_historical_data(self) -> None:
        """
        Charge les données historiques pour simuler les prix.
        """
        self.historical_data = {}
        
        # Vérifier si le répertoire de données existe
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir, exist_ok=True)
            logger.warning(f"Data directory '{self.data_dir}' created. Please add historical data files.")
            return
        
        # Parcourir les fichiers du répertoire
        for filename in os.listdir(self.data_dir):
            if not filename.endswith(".csv"):
                continue
            
            try:
                # Extraire le symbole et le timeframe du nom de fichier
                parts = filename.replace(".csv", "").split("_")
                
                if len(parts) >= 2:
                    symbol = "/".join(parts[:-1]) if len(parts) > 2 else parts[0]
                    timeframe = parts[-1]
                    
                    # Charger les données
                    file_path = os.path.join(self.data_dir, filename)
                    df = pd.read_csv(file_path)
                    
                    # Convertir la colonne timestamp en index
                    if 'timestamp' in df.columns:
                        df['timestamp'] = pd.to_datetime(df['timestamp'])
                        df.set_index('timestamp', inplace=True)
                    
                    # Stocker les données
                    if symbol not in self.historical_data:
                        self.historical_data[symbol] = {}
                    
                    self.historical_data[symbol][timeframe] = df
                    
                    logger.info(f"Loaded historical data for {symbol} {timeframe}: {len(df)} records")
                    
            except Exception as e:
                logger.error(f"Error loading historical data from {filename}: {str(e)}")
    
    def _get_current_ohlcv(self, symbol: str) -> tuple:
        """
        Récupère les données OHLCV actuelles pour un symbole donné.
        
        Args:
            symbol: Symbole de la paire
            
        Returns:
            Tuple (timestamp, données OHLCV)
        """
        # Vérifier si les données sont disponibles
        if symbol not in self.historical_data or "1m" not in self.historical_data[symbol]:
            return None, None
        
        # Récupérer les données
        df = self.historical_data[symbol]["1m"]
        
        # Incrémenter l'index temporel (simulation de l'avancement du temps)
        self.current_time_idx = (self.current_time_idx + 1) % len(df)
        
        # Récupérer les données actuelles
        current_time = df.index[self.current_time_idx]
        current_row = df.iloc[self.current_time_idx]
        
        # Créer le dictionnaire de données OHLCV
        ohlcv = {
            "open": current_row["open"],
            "high": current_row["high"],
            "low": current_row["low"],
            "close": current_row["close"],
            "volume": current_row["volume"]
        }
        
        return current_time, ohlcv
    
    def _generate_random_ticker(self, symbol: str) -> Dict:
        """
        Génère un ticker aléatoire pour un symbole donné.
        
        Args:
            symbol: Symbole de la paire
            
        Returns:
            Dictionnaire contenant les informations du ticker
        """
        # Prix de base par symbole
        base_prices = {
            "BTC/USDT": 95000.0,
            "ETH/USDT": 4500.0,
            "SOL/USDT": 240.0,
            "LINK/BTC": 0.00055
        }
        
        # Récupérer le prix de base ou utiliser une valeur par défaut
        base_price = base_prices.get(symbol, 100.0)
        
        # Générer un prix aléatoire autour du prix de base (± 2%)
        price = base_price * (1 + random.uniform(-0.02, 0.02))
        
        # Créer le ticker
        ticker = {
            "symbol": symbol,
            "timestamp": int(time.time() * 1000),
            "datetime": pd.Timestamp.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "high": price * (1 + random.uniform(0, 0.01)),
            "low": price * (1 - random.uniform(0, 0.01)),
            "bid": price * 0.999,
            "ask": price * 1.001,
            "last": price,
            "close": price,
            "previousClose": price * (1 - random.uniform(-0.01, 0.01)),
            "change": price * random.uniform(-0.01, 0.01),
            "percentage": random.uniform(-1, 1),
            "average": price,
            "baseVolume": random.uniform(10, 1000),
            "quoteVolume": random.uniform(10, 1000) * price,
            "info": {}
        }
        
        return ticker
    
    def _generate_random_ohlcv(self, limit: int) -> List:
        """
        Génère des données OHLCV aléatoires.
        
        Args:
            limit: Nombre de bougies à générer
            
        Returns:
            Liste de listes contenant les données OHLCV
        """
        ohlcv = []
        base_price = 100.0
        
        for i in range(limit):
            timestamp = int((time.time() - (limit - i) * 60) * 1000)  # 1 minute par bougie
            open_price = base_price * (1 + random.uniform(-0.02, 0.02))
            high_price = open_price * (1 + random.uniform(0, 0.01))
            low_price = open_price * (1 - random.uniform(0, 0.01))
            close_price = random.uniform(low_price, high_price)
            volume = random.uniform(10, 1000)
            
            ohlcv.append([
                timestamp,
                open_price,
                high_price,
                low_price,
                close_price,
                volume
            ])
            
            # Mettre à jour le prix de base pour la prochaine bougie
            base_price = close_price
        
        return ohlcv