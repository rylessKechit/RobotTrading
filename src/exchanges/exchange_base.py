"""
Classe de base pour les connecteurs d'échanges.
Définit l'interface commune pour interagir avec différents exchanges.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

class ExchangeBase(ABC):
    """
    Classe de base abstraite pour les connecteurs d'échanges.
    """
    
    def __init__(self, config: Dict):
        """
        Initialise le connecteur d'échange.
        
        Args:
            config: Configuration de l'échange
        """
        self.config = config
        self.name = config.get("name", "unknown")
        self.api_key = config.get("api_key", "")
        self.api_secret = config.get("api_secret", "")
        self.mode = config.get("mode", "paper_trading")
    
    @abstractmethod
    def connect(self) -> bool:
        """
        Établit la connexion avec l'échange.
        
        Returns:
            True si la connexion est établie avec succès, False sinon
        """
        pass
    
    @abstractmethod
    def get_balance(self) -> Dict:
        """
        Récupère le solde du compte.
        
        Returns:
            Dictionnaire contenant les soldes par devise
        """
        pass
    
    @abstractmethod
    def get_ticker(self, symbol: str) -> Dict:
        """
        Récupère le ticker pour un symbole donné.
        
        Args:
            symbol: Symbole de la paire (ex: "BTC/USDT")
            
        Returns:
            Dictionnaire contenant les informations du ticker
        """
        pass
    
    @abstractmethod
    def get_ohlcv(self, symbol: str, timeframe: str, limit: int = 100) -> List:
        """
        Récupère les données OHLCV pour un symbole et un timeframe donnés.
        
        Args:
            symbol: Symbole de la paire (ex: "BTC/USDT")
            timeframe: Intervalle de temps (ex: "1m", "5m", "1h")
            limit: Nombre de bougies à récupérer
            
        Returns:
            Liste de listes contenant les données OHLCV
        """
        pass
    
    @abstractmethod
    def create_order(self, symbol: str, order_type: str, side: str, amount: float, price: Optional[float] = None) -> Dict:
        """
        Crée un ordre sur l'échange.
        
        Args:
            symbol: Symbole de la paire (ex: "BTC/USDT")
            order_type: Type d'ordre ("MARKET", "LIMIT", etc.)
            side: Côté de l'ordre ("BUY", "SELL")
            amount: Quantité à acheter/vendre
            price: Prix pour les ordres limites (optionnel)
            
        Returns:
            Dictionnaire contenant les informations de l'ordre créé
        """
        pass
    
    @abstractmethod
    def cancel_order(self, order_id: str, symbol: str) -> bool:
        """
        Annule un ordre sur l'échange.
        
        Args:
            order_id: Identifiant de l'ordre
            symbol: Symbole de la paire
            
        Returns:
            True si l'ordre est annulé avec succès, False sinon
        """
        pass
    
    @abstractmethod
    def get_order(self, order_id: str, symbol: str) -> Dict:
        """
        Récupère les informations d'un ordre.
        
        Args:
            order_id: Identifiant de l'ordre
            symbol: Symbole de la paire
            
        Returns:
            Dictionnaire contenant les informations de l'ordre
        """
        pass
    
    @abstractmethod
    def get_open_orders(self, symbol: Optional[str] = None) -> List:
        """
        Récupère les ordres ouverts.
        
        Args:
            symbol: Symbole de la paire (optionnel)
            
        Returns:
            Liste des ordres ouverts
        """
        pass