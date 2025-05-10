"""
Fonctions pour le calcul des métriques de performance.
"""

import numpy as np
import pandas as pd

def calculate_roi(initial_capital, final_capital):
    """
    Calcule le Return on Investment (ROI).
    
    Args:
        initial_capital: Capital initial
        final_capital: Capital final
        
    Returns:
        ROI en pourcentage
    """
    if initial_capital == 0:
        return 0
    return (final_capital - initial_capital) / initial_capital

def calculate_cagr(initial_capital, final_capital, days):
    """
    Calcule le Compound Annual Growth Rate (CAGR).
    
    Args:
        initial_capital: Capital initial
        final_capital: Capital final
        days: Nombre de jours
        
    Returns:
        CAGR en pourcentage
    """
    if initial_capital == 0 or days == 0:
        return 0
    return ((final_capital / initial_capital) ** (365 / days)) - 1

def calculate_sharpe_ratio(returns, risk_free_rate=0.0):
    """
    Calcule le ratio de Sharpe.
    
    Args:
        returns: Liste des rendements (quotidiens ou autre période)
        risk_free_rate: Taux sans risque
        
    Returns:
        Ratio de Sharpe
    """
    if not returns or len(returns) < 2:
        return 0
    
    # Convertir en numpy array si nécessaire
    returns = np.array(returns)
    
    # Calculer les statistiques
    mean_return = np.mean(returns)
    std_return = np.std(returns)
    
    if std_return == 0:
        return 0
    
    # Annualiser (en supposant des rendements quotidiens)
    sharpe = (mean_return - risk_free_rate) / std_return * np.sqrt(252)
    
    return sharpe

def calculate_max_drawdown(equity_curve):
    """
    Calcule le drawdown maximum.
    
    Args:
        equity_curve: Liste ou tableau de valeurs d'équité
        
    Returns:
        Drawdown maximum en pourcentage
    """
    if not equity_curve or len(equity_curve) < 2:
        return 0
    
    # Convertir en numpy array si nécessaire
    equity = np.array(equity_curve)
    
    # Calculer le drawdown maximum
    peak = equity[0]
    max_dd = 0
    
    for value in equity:
        if value > peak:
            peak = value
        
        dd = (peak - value) / peak if peak > 0 else 0
        max_dd = max(max_dd, dd)
    
    return max_dd

def calculate_win_rate(trades):
    """
    Calcule le taux de réussite.
    
    Args:
        trades: Liste des trades avec profit_loss
        
    Returns:
        Taux de réussite en pourcentage
    """
    if not trades:
        return 0
    
    winning_trades = sum(1 for t in trades if t.get('profit_loss', 0) > 0)
    return winning_trades / len(trades)

def calculate_profit_factor(trades):
    """
    Calcule le facteur de profit.
    
    Args:
        trades: Liste des trades avec profit_loss
        
    Returns:
        Facteur de profit
    """
    if not trades:
        return 0
    
    gross_profit = sum(t.get('profit_loss', 0) for t in trades if t.get('profit_loss', 0) > 0)
    gross_loss = sum(abs(t.get('profit_loss', 0)) for t in trades if t.get('profit_loss', 0) < 0)
    
    if gross_loss == 0:
        return float('inf')
    
    return gross_profit / gross_loss