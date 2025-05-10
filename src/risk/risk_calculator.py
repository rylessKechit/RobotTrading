"""
Module pour calculer et gérer les risques liés au trading.
"""

from typing import Dict, Optional
import numpy as np

from ..utils.logger import get_logger

logger = get_logger(__name__)

class RiskCalculator:
    """
    Calcule les niveaux de risque et les métriques associées.
    """
    
    def __init__(self, config: Dict):
        """
        Initialise le calculateur de risque.
        
        Args:
            config: Configuration de la gestion des risques
        """
        self.config = config
        self.max_risk_per_trade = config.get("max_risk_per_trade", 0.01)  # 1% du capital par défaut
        self.max_position_size_pct = config.get("max_position_size_pct", 0.02)  # 2% du capital par défaut
        self.max_total_exposure = config.get("max_total_exposure", 0.70)  # 70% du capital par défaut
        self.max_consecutive_losses = config.get("max_consecutive_losses", 3)
        self.max_drawdown_pct = config.get("max_drawdown_pct", 0.10)  # 10% de drawdown max par défaut
    
    def calculate_position_size(self, capital: float, entry_price: float, stop_loss: float, max_risk_amount: Optional[float] = None) -> float:
        """
        Calcule la taille optimale d'une position en fonction du risque.
        
        Args:
            capital: Capital disponible
            entry_price: Prix d'entrée
            stop_loss: Niveau de stop loss
            max_risk_amount: Montant maximal à risquer (si None, utilise max_risk_per_trade)
            
        Returns:
            Taille de position optimale
        """
        # Calculer le risque en pourcentage
        if entry_price == 0 or stop_loss == 0:
            logger.warning("Entry price or stop loss is zero, cannot calculate position size")
            return 0.0
        
        risk_pct = abs(entry_price - stop_loss) / entry_price
        
        if risk_pct == 0:
            logger.warning("Risk percentage is zero, cannot calculate position size")
            return 0.0
        
        # Suite de risk_calculator.py

        # Calculer le montant à risquer
        if max_risk_amount is None:
            max_risk_amount = capital * self.max_risk_per_trade
        
        # Calculer la taille de position basée sur le risque
        position_size = max_risk_amount / risk_pct
        
        # Limiter la taille de position au maximum autorisé
        max_position_size = capital * self.max_position_size_pct
        position_size = min(position_size, max_position_size)
        
        return position_size
    
    def calculate_risk_reward_ratio(self, entry_price: float, stop_loss: float, take_profit: float, direction: str) -> float:
        """
        Calcule le ratio risque/récompense d'une position.
        
        Args:
            entry_price: Prix d'entrée
            stop_loss: Niveau de stop loss
            take_profit: Niveau de take profit
            direction: Direction de la position ('LONG' ou 'SHORT')
            
        Returns:
            Ratio risque/récompense
        """
        if direction == "LONG":
            risk = entry_price - stop_loss
            reward = take_profit - entry_price
        else:  # SHORT
            risk = stop_loss - entry_price
            reward = entry_price - take_profit
        
        if risk <= 0:
            logger.warning("Risk is zero or negative, cannot calculate risk/reward ratio")
            return 0.0
        
        return reward / risk
    
    def is_drawdown_acceptable(self, equity_curve: list, current_equity: float) -> bool:
        """
        Vérifie si le drawdown actuel est acceptable.
        
        Args:
            equity_curve: Historique de l'équité
            current_equity: Équité actuelle
            
        Returns:
            True si le drawdown est acceptable, False sinon
        """
        if not equity_curve:
            return True
        
        # Calculer le drawdown actuel
        peak_equity = max(equity_curve)
        drawdown = (peak_equity - current_equity) / peak_equity
        
        return drawdown <= self.max_drawdown_pct
    
    def can_open_position(self, current_positions: Dict, consecutive_losses: int, equity_curve: list, current_equity: float) -> bool:
        """
        Vérifie si une nouvelle position peut être ouverte en fonction des règles de gestion des risques.
        
        Args:
            current_positions: Positions actuellement ouvertes
            consecutive_losses: Nombre de pertes consécutives
            equity_curve: Historique de l'équité
            current_equity: Équité actuelle
            
        Returns:
            True si une nouvelle position peut être ouverte, False sinon
        """
        # Vérifier le nombre de pertes consécutives
        if consecutive_losses >= self.max_consecutive_losses:
            logger.info(f"Maximum consecutive losses reached ({consecutive_losses}), cannot open new position")
            return False
        
        # Vérifier le drawdown
        if not self.is_drawdown_acceptable(equity_curve, current_equity):
            logger.info("Maximum drawdown reached, cannot open new position")
            return False
        
        # Vérifier l'exposition totale
        total_exposure = sum(position["position_value"] for position in current_positions.values())
        if total_exposure >= current_equity * self.max_total_exposure:
            logger.info(f"Maximum exposure reached ({total_exposure:.2f}), cannot open new position")
            return False
        
        return True