#!/usr/bin/env python3
"""
Script pour exécuter un backtest du Robot Trader Crypto sur des données historiques.
"""

import os
import sys
import argparse
import logging
import json
import time
from datetime import datetime
import matplotlib.pyplot as plt

# Ajouter le répertoire parent au chemin de recherche des modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Importer les modules nécessaires
try:
    from src.backtesting.backtest_engine import BacktestEngine
    from src.strategies import get_strategy
    from src.utils.logger import setup_logger
except ImportError as e:
    print(f"Erreur d'importation: {e}")
    print("Assurez-vous que tous les modules nécessaires sont installés et que la structure du projet est correcte.")
    sys.exit(1)

def main():
    """
    Fonction principale.
    """
    # Analyser les arguments de la ligne de commande
    parser = argparse.ArgumentParser(description="Backtest pour Robot Trader Crypto")
    parser.add_argument("--config", default="config/backtest_config.json", help="Chemin vers le fichier de configuration du backtest")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], help="Niveau de journalisation")
    parser.add_argument("--output-dir", default="backtest_results", help="Répertoire pour sauvegarder les résultats")
    parser.add_argument("--plot", action="store_true", help="Générer des graphiques")
    parser.add_argument("--report", action="store_true", help="Générer un rapport HTML")
    args = parser.parse_args()
    
    # Configurer la journalisation
    setup_logger(args.log_level)
    logger = logging.getLogger(__name__)
    
    # Vérifier si le fichier de configuration existe
    if not os.path.exists(args.config):
        logger.error(f"Le fichier de configuration '{args.config}' n'existe pas.")
        sys.exit(1)
    
    # Charger la configuration
    try:
        with open(args.config, 'r') as f:
            config = json.load(f)
    except Exception as e:
        logger.error(f"Erreur lors du chargement de la configuration: {str(e)}")
        sys.exit(1)
    
    # Créer le répertoire de sortie s'il n'existe pas
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Afficher les informations de configuration
    logger.info("Démarrage du backtest avec la configuration suivante:")
    logger.info(f"- Paires de trading: {', '.join(config.get('trading_pairs', []))}")
    logger.info(f"- Période: {config.get('start_date', '')} - {config.get('end_date', '')}")
    
    # Exécuter le backtest
    try:
        start_time = time.time()
        
        # Initialiser le moteur de backtest
        backtest_engine = BacktestEngine(config)
        
        # Charger les données historiques
        backtest_engine.load_data()
        
        # Obtenir la stratégie
        strategy_name = config.get("strategy_params", {}).get("name", "scalping")
        strategy_params = config.get("strategy_params", {})
        
        strategy_class = get_strategy(strategy_name)
        if strategy_class is None:
            logger.error(f"Stratégie '{strategy_name}' non trouvée.")
            sys.exit(1)
        
        strategy = strategy_class(config)
        
        # Exécuter le backtest
        logger.info(f"Exécution du backtest avec la stratégie '{strategy_name}'...")
        results = backtest_engine.run(strategy)
        
        # Calculer le temps d'exécution
        execution_time = time.time() - start_time
        logger.info(f"Backtest terminé en {execution_time:.2f} secondes.")
        
        # Afficher les résultats
        metrics = results.get("metrics", {})
        trades = results.get("trades", [])
        
        print("\n" + "="*50)
        print("RÉSULTATS DU BACKTEST")
        print("="*50)
        print(f"Période: {config.get('start_date', '').split('T')[0]} - {config.get('end_date', '').split('T')[0]}")
        print(f"Paires: {', '.join(config.get('trading_pairs', []))}")
        print(f"Capital initial: ${metrics.get('initial_capital', 0):.2f}")
        print(f"Capital final: ${metrics.get('final_capital', 0):.2f}")
        print(f"Profit total: ${metrics.get('total_return', 0):.2f} ({metrics.get('roi', 0)*100:.2f}%)")
        print(f"CAGR: {metrics.get('cagr', 0)*100:.2f}%")
        print(f"Nombre de trades: {metrics.get('total_trades', 0)}")
        print(f"Taux de réussite: {metrics.get('win_rate', 0)*100:.2f}%")
        print(f"Ratio Sharpe: {metrics.get('sharpe_ratio', 0):.2f}")
        print(f"Drawdown maximum: {metrics.get('max_drawdown', 0)*100:.2f}%")
        print("="*50)
        
        # Sauvegarder les résultats
        results_file = os.path.join(args.output_dir, "backtest_results.json")
        with open(results_file, 'w') as f:
            # Convertir les timestamps en chaînes pour la sérialisation JSON
            serializable_results = results.copy()
            serializable_results["equity_curve"] = [(str(dt), val) for dt, val in results["equity_curve"]]
            
            for trade in serializable_results["trades"]:
                for key in ["entry_time", "exit_time"]:
                    if key in trade and trade[key] is not None:
                        trade[key] = str(trade[key])
            
            json.dump(serializable_results, f, indent=4)
        
        logger.info(f"Résultats sauvegardés dans {results_file}")
        
        # Générer des graphiques si demandé
        if args.plot:
            plot_file = os.path.join(args.output_dir, "backtest_results.png")
            backtest_engine.plot_results(plot_file)
            logger.info(f"Graphiques sauvegardés dans {plot_file}")
        
        # Générer un rapport HTML si demandé
        if args.report:
            report_file = os.path.join(args.output_dir, "backtest_report.html")
            # Si la méthode generate_report existe
            if hasattr(backtest_engine, "generate_report"):
                backtest_engine.generate_report(report_file)
                logger.info(f"Rapport HTML sauvegardé dans {report_file}")
        
        return results
        
    except KeyboardInterrupt:
        logger.info("Backtest interrompu par l'utilisateur.")
        return None
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution du backtest: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

# Fonction pour créer un fichier de configuration par défaut
def create_default_config(output_path):
    """
    Crée un fichier de configuration par défaut pour le backtest.
    
    Args:
        output_path: Chemin où sauvegarder le fichier de configuration
    """
    config = {
        "exchange": {
            "name": "binance",
            "api_key": "",
            "api_secret": ""
        },
        "trading_pairs": ["BTC/USDT", "ETH/USDT"],
        "start_date": "2023-01-01T00:00:00",
        "end_date": "2023-12-31T23:59:59",
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
    
    # Créer le répertoire parent si nécessaire
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Sauvegarder la configuration
    with open(output_path, 'w') as f:
        json.dump(config, f, indent=4)
    
    print(f"Configuration par défaut créée: {output_path}")

if __name__ == "__main__":
    # Vérifier si l'option --create-config est spécifiée
    if len(sys.argv) > 1 and sys.argv[1] == "--create-config":
        output_path = "config/backtest_config.json"
        if len(sys.argv) > 2:
            output_path = sys.argv[2]
        create_default_config(output_path)
    else:
        main()