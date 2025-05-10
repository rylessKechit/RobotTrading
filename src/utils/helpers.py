"""
Fonctions utilitaires diverses pour le Robot Trader Crypto.
"""

import json
from datetime import datetime
from decimal import Decimal

def format_number(number, precision=8):
    """
    Formate un nombre avec la précision spécifiée.
    
    Args:
        number: Nombre à formater
        precision: Nombre de décimales
        
    Returns:
        Nombre formaté
    """
    if number is None:
        return None
        
    format_str = f"{{:.{precision}f}}"
    return float(format_str.format(number))

def get_candle_timestamp(timestamp, timeframe):
    """
    Calcule le timestamp de début de bougie pour un timestamp donné.
    
    Args:
        timestamp: Timestamp en secondes ou millisecondes
        timeframe: Intervalle de temps (ex: '1m', '5m', '1h')
        
    Returns:
        Timestamp de début de bougie
    """
    # Convertir en timestamp en secondes si nécessaire
    if timestamp > 10**12:  # Si en millisecondes
        timestamp = timestamp / 1000
    
    # Convertir le timeframe en secondes
    from .timeframe import timeframe_to_seconds
    interval_seconds = timeframe_to_seconds(timeframe)
    
    # Calculer le timestamp de début de bougie
    return int(timestamp - (timestamp % interval_seconds)) * 1000  # Retourner en millisecondes

def json_serialize(obj):
    """
    Fonction de sérialisation personnalisée pour JSON.
    
    Args:
        obj: Objet à sérialiser
        
    Returns:
        Représentation sérialisable de l'objet
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Type non sérialisable: {type(obj)}")