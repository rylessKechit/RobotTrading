"""
Module principal du Robot Trader Crypto.
Gère l'exécution des stratégies et l'interaction avec les exchanges.
"""

import time
import threading
from typing import Dict, List, Optional

from ..utils.logger import get_logger
from ..core.event_system import EventSystem
from ..core.data_manager import DataManager
from ..core.config_manager import ConfigManager
from ..exchanges.exchange_base import ExchangeBase
from ..strategies.base_strategy import BaseStrategy
from ..risk.exposure_manager import ExposureManager

logger = get_logger(__name__)

class TradingBot:
    """
    Classe principale du Robot Trader Crypto.
    """
    
    def __init__(self, config_path: str = "config/config.json"):
        """
        Initialise le robot trader.
        
        Args:
            config_path: Chemin vers le fichier de configuration
        """
        self.config_manager = ConfigManager(config_path)
        self.config = self.config_manager.get_config()
        
        # Initialiser le système d'événements
        self.event_system = EventSystem()
        
        # Initialiser le gestionnaire de données
        self.data_manager = DataManager(self.config)
        
        # Initialiser l'exchange
        exchange_class = self._get_exchange_class()
        self.exchange = exchange_class(self.config.get("exchange", {}))
        
        # Initialiser le gestionnaire d'exposition
        self.exposure_manager = ExposureManager(
            self.config.get("risk_management", {}),
            self.exchange
        )
        
        # Charger la stratégie
        strategy_class = self._get_strategy_class()
        self.strategy = strategy_class(
            self.config.get("strategy", {}),
            self.data_manager,
            self.exchange,
            self.exposure_manager,
            self.event_system
        )
        
        # État du bot
        self.is_running = False
        self.bot_thread = None
        self.positions = {}
        self.performance_metrics = {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "total_profit": 0,
            "max_drawdown": 0,
            "consecutive_losses": 0
        }
        
        logger.info("Bot initialized successfully")
    
    def _get_exchange_class(self):
        """
        Récupère la classe d'exchange appropriée en fonction de la configuration.
        """
        from ..exchanges import get_exchange
        exchange_name = self.config.get("exchange", {}).get("name", "binance")
        return get_exchange(exchange_name)
    
    def _get_strategy_class(self):
        """
        Récupère la classe de stratégie appropriée en fonction de la configuration.
        """
        from ..strategies import get_strategy
        strategy_name = self.config.get("strategy", {}).get("name", "scalping")
        return get_strategy(strategy_name)
    
    def start(self, interval_seconds: int = 60):
        """
        Démarre le robot trader en boucle continue.
        
        Args:
            interval_seconds: Intervalle entre les cycles de trading
        """
        if self.is_running:
            logger.warning("Bot is already running")
            return
        
        logger.info("Starting trading bot")
        self.is_running = True
        
        # Démarrer le bot dans un thread séparé
        self.bot_thread = threading.Thread(target=self._run_loop, args=(interval_seconds,))
        self.bot_thread.daemon = True
        self.bot_thread.start()
    
    def stop(self):
        """
        Arrête le robot trader.
        """
        if not self.is_running:
            logger.warning("Bot is not running")
            return
        
        logger.info("Stopping trading bot")
        self.is_running = False
        
        # Attendre la fin du thread
        if self.bot_thread and self.bot_thread.is_alive():
            self.bot_thread.join(timeout=10)
        
        # Fermer toutes les positions si nécessaire
        if self.config.get("close_positions_on_stop", True):
            self._close_all_positions()
    
    def _run_loop(self, interval_seconds: int):
        """
        Boucle principale du robot.
        
        Args:
            interval_seconds: Intervalle entre les cycles de trading
        """
        while self.is_running:
            try:
                start_time = time.time()
                
                # Mettre à jour les données de marché
                self.data_manager.update_market_data()
                
                # Exécuter la stratégie
                self.strategy.execute()
                
                # Mettre à jour les positions
                self._update_positions()
                
                # Mettre à jour les métriques de performance
                self._update_performance_metrics()
                
                # Attendre jusqu'au prochain cycle
                elapsed = time.time() - start_time
                wait_time = max(0, interval_seconds - elapsed)
                
                if wait_time > 0:
                    time.sleep(wait_time)
            
            except Exception as e:
                logger.error(f"Error in trading cycle: {str(e)}")
                # Continuer malgré l'erreur
    
    def _update_positions(self):
        """
        Met à jour l'état des positions ouvertes.
        """
        # Implémentation spécifique pour mettre à jour les positions
        pass
    
    def _update_performance_metrics(self):
        """
        Met à jour les métriques de performance.
        """
        # Implémentation spécifique pour mettre à jour les métriques
        pass
    
    def _close_all_positions(self):
        """
        Ferme toutes les positions ouvertes.
        """
        # Implémentation spécifique pour fermer les positions
        pass
    
    def get_status(self) -> Dict:
        """
        Retourne l'état actuel du bot.
        """
        return {
            "is_running": self.is_running,
            "positions": self.positions,
            "performance": self.performance_metrics,
            "balance": self.exchange.get_balance()
        }