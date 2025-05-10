"""
Module de configuration de la journalisation.
"""

import os
import logging
from datetime import datetime

# Configuration globale du logger
def setup_logger(level="INFO", log_file=None):
    """
    Configure le système de journalisation.
    
    Args:
        level: Niveau de journalisation (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Chemin vers le fichier de journalisation (optionnel)
    """
    # Convertir le niveau de log en constante logging
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Niveau de log invalide : {level}")
    
    # Créer le répertoire des logs si nécessaire
    if log_file:
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
    else:
        # Log par défaut dans le dossier data/logs
        logs_dir = "data/logs"
        os.makedirs(logs_dir, exist_ok=True)
        
        # Nom de fichier basé sur la date
        date_str = datetime.now().strftime("%Y-%m-%d")
        log_file = f"{logs_dir}/robot_trader_{date_str}.log"
    
    # Configurer le handler de fichier
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    
    # Configurer le handler de console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    
    # Configurer le root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Supprimer les handlers existants pour éviter les doublons
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Ajouter les nouveaux handlers
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    return root_logger

def get_logger(name):
    """
    Récupère un logger configuré pour un module spécifique.
    
    Args:
        name: Nom du module (généralement __name__)
        
    Returns:
        Instance de logger configurée
    """
    return logging.getLogger(name)