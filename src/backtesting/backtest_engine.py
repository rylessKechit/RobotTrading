"""
Moteur de backtesting pour tester les stratégies de trading sur des données historiques.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union, Tuple
import matplotlib.pyplot as plt
from datetime import datetime

from ..utils.logger import get_logger
from ..strategies.base_strategy import BaseStrategy
from .data_loader import DataLoader
from .simulator import OrderSimulator
from .reporter import BacktestReporter

logger = get_logger(__name__)

class BacktestEngine:
    """
    Moteur de backtesting pour tester les stratégies de trading sur des données historiques.
    """
    
    def __init__(self, config: Dict):
        """
        Initialise le moteur de backtesting.
        
        Args:
            config: Configuration du backtest
        """
        self.config = config
        self.start_date = pd.Timestamp(config.get("start_date", "2024-01-01T00:00:00"))
        self.end_date = pd.Timestamp(config.get("end_date", "2024-12-31T23:59:59"))
        self.pairs = config.get("trading_pairs", ["BTC/USDT"])
        
        # Paramètres du backtest
        self.initial_capital = config.get("risk_management", {}).get("initial_capital", 10000)
        
        # Initialiser le chargeur de données
        self.data_loader = DataLoader(config)
        
        # Initialiser le simulateur d'ordres
        self.simulator = OrderSimulator(config)
        
        # Initialiser le rapporteur de backtest
        self.reporter = BacktestReporter()
        
        # Résultats du backtest
        self.results = {
            "trades": [],
            "equity_curve": [],
            "metrics": {}
        }
        
        logger.info(f"Backtest engine initialized for period {self.start_date.date()} to {self.end_date.date()}")
    
    def load_data(self) -> bool:
        """
        Charge les données historiques pour le backtest.
        
        Returns:
            True si les données sont chargées avec succès, False sinon
        """
        try:
            logger.info("Loading historical data...")
            self.market_data = self.data_loader.load_data(self.pairs, self.start_date, self.end_date)
            logger.info(f"Data loaded for {len(self.pairs)} pairs")
            return True
        except Exception as e:
            logger.error(f"Error loading data: {str(e)}")
            return False
    
    def run(self, strategy: BaseStrategy) -> Dict:
        """
        Exécute le backtest avec la stratégie donnée.
        
        Args:
            strategy: Stratégie à tester
            
        Returns:
            Résultats du backtest
        """
        if not hasattr(self, 'market_data'):
            if not self.load_data():
                return self.results
        
        logger.info(f"Running backtest with {strategy.__class__.__name__}")
        
        # Préparation du backtest
        equity = self.initial_capital
        equity_curve = [(self.start_date, equity)]
        trades = []
        positions = {}
        
        # Parcourir les données chronologiquement
        time_index = self._create_time_index()
        
        for current_time in time_index:
            # Mettre à jour les données de marché jusqu'à current_time
            market_data_slice = self._slice_data_to_time(current_time)
            
            # Mettre à jour la stratégie avec les données actuelles
            strategy.update_data(market_data_slice)
            
            # Vérifier les positions ouvertes
            positions = self._update_positions(positions, current_time, trades, equity)
            
            # Générer les signaux de la stratégie
            signals = strategy.generate_signals(current_time)
            
            # Exécuter les signaux
            for signal in signals:
                # Vérifier si nous pouvons ouvrir la position
                if self.simulator.can_open_position(signal, positions, equity):
                    # Simuler l'ouverture de la position
                    position = self.simulator.open_position(signal, current_time, equity)
                    positions[position["id"]] = position
                    logger.debug(f"Opened {position['direction']} position on {position['pair']} at {position['entry_price']}")
            
            # Mettre à jour l'équité
            equity = self._calculate_equity(positions, equity, current_time)
            equity_curve.append((current_time, equity))
        
        # Fermer toutes les positions restantes à la fin du backtest
        for position_id, position in list(positions.items()):
            position = self.simulator.close_position(
                position, 
                self.end_date, 
                self._get_close_price(position["pair"], self.end_date),
                "END_OF_BACKTEST"
            )
            trades.append(position)
            positions.pop(position_id)
        
        # Calculer les métriques finales
        final_equity = equity
        metrics = self._calculate_metrics(trades, equity_curve, self.initial_capital)
        
        # Stocker les résultats
        self.results = {
            "trades": trades,
            "equity_curve": equity_curve,
            "metrics": metrics
        }
        
        # Générer le rapport
        self.reporter.generate_report(self.results, self.config)
        
        logger.info(f"Backtest completed: Initial capital ${self.initial_capital:.2f}, Final capital ${final_equity:.2f}, ROI {metrics['roi']*100:.2f}%")
        
        return self.results
    
    def _create_time_index(self) -> pd.DatetimeIndex:
        """
        Crée un index temporel pour parcourir les données chronologiquement.
        
        Returns:
            Index temporel
        """
        # Fusionner les index de toutes les données de marché
        all_timestamps = set()
        
        for pair, timeframes in self.market_data.items():
            for timeframe, df in timeframes.items():
                all_timestamps.update(df.index.tolist())
        
        # Créer un index trié
        time_index = pd.DatetimeIndex(sorted(all_timestamps))
        
        # Filtrer l'index pour la période du backtest
        time_index = time_index[(time_index >= self.start_date) & (time_index <= self.end_date)]
        
        return time_index
    
    def _slice_data_to_time(self, current_time: pd.Timestamp) -> Dict:
        """
        Découpe les données de marché jusqu'à un moment donné.
        
        Args:
            current_time: Moment actuel
            
        Returns:
            Données de marché jusqu'à current_time
        """
        sliced_data = {}
        
        for pair, timeframes in self.market_data.items():
            sliced_data[pair] = {}
            
            for timeframe, df in timeframes.items():
                sliced_data[pair][timeframe] = df[df.index <= current_time]
        
        return sliced_data
    
    def _update_positions(self, positions: Dict, current_time: pd.Timestamp, trades: List, equity: float) -> Dict:
        """
        Met à jour les positions ouvertes.
        
        Args:
            positions: Positions actuellement ouvertes
            current_time: Moment actuel
            trades: Liste des trades complétés
            equity: Capital actuel
            
        Returns:
            Positions mises à jour
        """
        for position_id, position in list(positions.items()):
            pair = position["pair"]
            current_price = self._get_close_price(pair, current_time)
            
            # Vérifier les conditions de sortie
            exit_reason = self._check_exit_conditions(position, current_price, current_time)
            
            if exit_reason:
                # Fermer la position
                closed_position = self.simulator.close_position(
                    position,
                    current_time,
                    current_price,
                    exit_reason
                )
                
                trades.append(closed_position)
                positions.pop(position_id)
                
                logger.debug(f"Closed {position['direction']} position on {pair} at {current_price}, reason: {exit_reason}")
        
        return positions
    
    def _check_exit_conditions(self, position: Dict, current_price: float, current_time: pd.Timestamp) -> Optional[str]:
        """
        Vérifie si les conditions de sortie sont remplies.
        
        Args:
            position: Position à vérifier
            current_price: Prix actuel
            current_time: Moment actuel
            
        Returns:
            Raison de sortie si les conditions sont remplies, None sinon
        """
        direction = position["direction"]
        entry_price = position["entry_price"]
        stop_loss = position["stop_loss"]
        take_profit1 = position["take_profit1"]
        take_profit2 = position["take_profit2"]
        
        # Vérifier le stop loss
        if (direction == "LONG" and current_price <= stop_loss) or \
           (direction == "SHORT" and current_price >= stop_loss):
            return "STOP_LOSS"
        
        # Vérifier les take profits (en fonction de ce qui a déjà été atteint)
        if "exit_take_profit1" not in position:
            if (direction == "LONG" and current_price >= take_profit1) or \
               (direction == "SHORT" and current_price <= take_profit1):
                return "TAKE_PROFIT1"
        
        if "exit_take_profit1" in position and "exit_take_profit2" not in position:
            if (direction == "LONG" and current_price >= take_profit2) or \
               (direction == "SHORT" and current_price <= take_profit2):
                return "TAKE_PROFIT2"
        
        # Vérifier le trailing stop (si activé)
        if "trailing_stop" in position and position["trailing_activated"]:
            trailing_stop = position["trailing_stop"]
            
            if (direction == "LONG" and current_price <= trailing_stop) or \
               (direction == "SHORT" and current_price >= trailing_stop):
                return "TRAILING_STOP"
        
        # Mettre à jour le trailing stop si nécessaire
        self._update_trailing_stop(position, current_price)
        
        # Vérifier la durée maximale de la position
        max_duration = pd.Timedelta(hours=self.config.get("max_position_duration_hours", 48))
        if current_time - position["entry_time"] > max_duration:
            return "TIME_LIMIT"
        
        return None
    
    def _update_trailing_stop(self, position: Dict, current_price: float) -> None:
        """
        Met à jour le trailing stop d'une position.
        
        Args:
            position: Position à mettre à jour
            current_price: Prix actuel
        """
        direction = position["direction"]
        trailing_pct = position.get("trailing_stop_pct", 0.003)
        
        # Pour les positions longues
        if direction == "LONG":
            # Initialiser le prix le plus haut si nécessaire
            if "highest_price" not in position:
                position["highest_price"] = position["entry_price"]
            
            # Mettre à jour le prix le plus haut si le prix actuel est plus élevé
            if current_price > position["highest_price"]:
                position["highest_price"] = current_price
                
                # Calculer le nouveau trailing stop
                position["trailing_stop"] = current_price * (1 - trailing_pct)
                position["trailing_activated"] = True
        
        # Pour les positions courtes
        elif direction == "SHORT":
            # Initialiser le prix le plus bas si nécessaire
            if "lowest_price" not in position:
                position["lowest_price"] = position["entry_price"]
            
            # Mettre à jour le prix le plus bas si le prix actuel est plus bas
            if current_price < position["lowest_price"]:
                position["lowest_price"] = current_price
                
                # Calculer le nouveau trailing stop
                position["trailing_stop"] = current_price * (1 + trailing_pct)
                position["trailing_activated"] = True
    
    def _get_close_price(self, pair: str, timestamp: pd.Timestamp) -> float:
        """
        Récupère le prix de clôture le plus proche pour une paire à un moment donné.
        
        Args:
            pair: Paire de trading
            timestamp: Moment pour lequel récupérer le prix
            
        Returns:
            Prix de clôture
        """
        # Utiliser le timeframe primaire par défaut
        primary_timeframe = self.config.get("timeframes", {}).get("primary", "5m")
        
        # Récupérer les données pour la paire et le timeframe
        df = self.market_data.get(pair, {}).get(primary_timeframe, None)
        
        if df is None or df.empty:
            logger.warning(f"No data available for {pair} at {timestamp}")
            return 0.0
        
        # Trouver l'index le plus proche
        idx = df.index.get_indexer([timestamp], method='nearest')[0]
        
        if idx < 0 or idx >= len(df):
            logger.warning(f"Index out of bounds for {pair} at {timestamp}")
            return 0.0
        
        return df['close'].iloc[idx]
    
    def _calculate_equity(self, positions: Dict, current_equity: float, current_time: pd.Timestamp) -> float:
        """
        Calcule l'équité actuelle en tenant compte des positions ouvertes.
        
        Args:
            positions: Positions actuellement ouvertes
            current_equity: Équité actuelle
            current_time: Moment actuel
            
        Returns:
            Équité mise à jour
        """
        # Calculer la valeur des positions ouvertes
        positions_value = 0.0
        
        for position in positions.values():
            pair = position["pair"]
            direction = position["direction"]
            entry_price = position["entry_price"]
            position_size = position["position_size"]
            current_price = self._get_close_price(pair, current_time)
            
            # Calculer le P&L non réalisé
            if direction == "LONG":
                pnl = (current_price - entry_price) / entry_price * position_size * entry_price
            else:  # SHORT
                pnl = (entry_price - current_price) / entry_price * position_size * entry_price
            
            positions_value += pnl
        
        # Ajouter le capital initial
        return self.initial_capital + positions_value
    
    def _calculate_metrics(self, trades: List, equity_curve: List, initial_capital: float) -> Dict:
        """
        Calcule les métriques de performance du backtest.
        
        Args:
            trades: Liste des trades complétés
            equity_curve: Courbe d'équité
            initial_capital: Capital initial
            
        Returns:
            Métriques de performance
        """
        # Extraire les valeurs d'équité
        equity_values = [eq[1] for eq in equity_curve]
        dates = [eq[0] for eq in equity_curve]
        
        # Calculer les métriques de base
        final_equity = equity_values[-1] if equity_values else initial_capital
        total_return = final_equity - initial_capital
        roi = total_return / initial_capital
        
        # Calculer le CAGR (Compound Annual Growth Rate)
        days = (dates[-1] - dates[0]).days if dates else 0
        cagr = ((final_equity / initial_capital) ** (365 / max(days, 1)) - 1) if days > 0 else 0
        
        # Calculer les métriques de trades
        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if t.get("profit_loss", 0) > 0)
        losing_trades = total_trades - winning_trades
        
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # Calculer le profit moyen et la perte moyenne
        avg_profit = sum(t.get("profit_loss", 0) for t in trades if t.get("profit_loss", 0) > 0) / winning_trades if winning_trades > 0 else 0
        avg_loss = sum(abs(t.get("profit_loss", 0)) for t in trades if t.get("profit_loss", 0) <= 0) / losing_trades if losing_trades > 0 else 0
        
        # Calculer le ratio profit/perte
        profit_factor = avg_profit / avg_loss if avg_loss > 0 else float('inf')
        
        # Calculer le drawdown maximal
        max_drawdown = 0.0
        peak_equity = initial_capital
        
        for equity in equity_values:
            if equity > peak_equity:
                peak_equity = equity
            else:
                drawdown = (peak_equity - equity) / peak_equity
                max_drawdown = max(max_drawdown, drawdown)
        
        # Calculer le Sharpe Ratio (simplifié)
        if len(equity_values) > 1:
            returns = []
            for i in range(1, len(equity_values)):
                prev_equity = equity_values[i-1]
                curr_equity = equity_values[i]
                if prev_equity > 0:
                    returns.append((curr_equity - prev_equity) / prev_equity)
            
            avg_return = sum(returns) / len(returns) if returns else 0
            std_return = (sum([(r - avg_return) ** 2 for r in returns]) / len(returns)) ** 0.5 if returns else 0
            sharpe = (avg_return / std_return * (252 ** 0.5)) if std_return > 0 else 0
        else:
            sharpe = 0
        
        return {
            "initial_capital": initial_capital,
            "final_capital": final_equity,
            "total_return": total_return,
            "roi": roi,
            "cagr": cagr,
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": win_rate,
            "avg_profit": avg_profit,
            "avg_loss": avg_loss,
            "profit_factor": profit_factor,
            "max_drawdown": max_drawdown,
            "sharpe_ratio": sharpe
        }
    
    def plot_results(self, output_file: str = "backtest_results.png") -> None:
        """
        Visualise les résultats du backtest.
        
        Args:
            output_file: Nom du fichier pour sauvegarder le graphique
        """
        if not self.results['equity_curve']:
            logger.warning("No results to plot")
            return
            
        # Configurer la figure
        plt.figure(figsize=(16, 10))
        
        # Tracer la courbe d'équité
        plt.subplot(3, 1, 1)
        
        dates = [eq[0] for eq in self.results['equity_curve']]
        equity = [eq[1] for eq in self.results['equity_curve']]
        
        plt.plot(dates, equity, 'b-')
        plt.title('Courbe d\'équité')
        plt.ylabel('Capital ($)')
        plt.grid(True)
        
        # Tracer les trades
        plt.subplot(3, 1, 2)
        
        # Extraire les données des trades
        long_entries = [(t['entry_time'], t['entry_price']) for t in self.results['trades'] if t['direction'] == 'LONG']
        long_exits = [(t['exit_time'], t['exit_price']) for t in self.results['trades'] if t['direction'] == 'LONG' and 'exit_price' in t]
        
        short_entries = [(t['entry_time'], t['entry_price']) for t in self.results['trades'] if t['direction'] == 'SHORT']
        short_exits = [(t['exit_time'], t['exit_price']) for t in self.results['trades'] if t['direction'] == 'SHORT' and 'exit_price' in t]
        
        # Sélectionner une paire représentative pour le graphique
        if self.pairs:
            main_pair = self.pairs[0]
            primary_timeframe = self.config.get("timeframes", {}).get("primary", "5m")
            
            # Récupérer les données pour la paire et le timeframe
            df = self.market_data.get(main_pair, {}).get(primary_timeframe, None)
            
            if df is not None:
                plt.plot(df.index, df['close'], 'k-', alpha=0.5, label=f'{main_pair} Close')
                
                # Marquer les entrées/sorties
                if long_entries:
                    entry_dates, entry_prices = zip(*long_entries)
                    plt.scatter(entry_dates, entry_prices, color='green', marker='^', s=100, label='Long Entry')
                
                if long_exits:
                    exit_dates, exit_prices = zip(*long_exits)
                    plt.scatter(exit_dates, exit_prices, color='red', marker='v', s=100, label='Long Exit')
                
                if short_entries:
                    entry_dates, entry_prices = zip(*short_entries)
                    plt.scatter(entry_dates, entry_prices, color='red', marker='v', s=100, label='Short Entry')
                
                if short_exits:
                    exit_dates, exit_prices = zip(*short_exits)
                    plt.scatter(exit_dates, exit_prices, color='green', marker='^', s=100, label='Short Exit')
                
                plt.title(f'Transactions sur {main_pair}')
                plt.ylabel('Prix')
                plt.legend()
                plt.grid(True)
        
        # Tracer les métriques de performance
        plt.subplot(3, 1, 3)
        
        metrics = self.results['metrics']
        
        # Créer un graphique en barres avec les principales métriques
        metrics_labels = ['ROI', 'Win Rate', 'Profit Factor', 'Max Drawdown']
        metrics_values = [
            metrics['roi'],
            metrics['win_rate'],
            min(metrics['profit_factor'], 10),  # Limiter pour la lisibilité
            metrics['max_drawdown']
        ]
        
        colors = ['green' if v > 0 else 'red' for v in metrics_values]
        plt.bar(metrics_labels, metrics_values, color=colors)
        plt.title('Métriques de performance')
        plt.ylabel('Valeur')
        plt.grid(True)
        
        # Ajouter les annotations avec les valeurs précises
        for i, v in enumerate(metrics_values):
            if metrics_labels[i] == 'Profit Factor' and metrics['profit_factor'] > 10:
                plt.text(i, v + 0.05, f"∞", ha='center')
            else:
                plt.text(i, v + 0.05, f"{v:.2f}" if isinstance(v, float) else str(v), ha='center')
        
        # Ajouter un texte récapitulatif
        summary_text = (
            f"Capital initial: ${metrics['initial_capital']:.0f}\n"
            f"Capital final: ${metrics['final_capital']:.0f}\n"
            f"Profit total: ${metrics['total_return']:.0f}\n"
            f"Nombre de trades: {metrics['total_trades']}\n"
            f"Trades gagnants: {metrics['winning_trades']} ({metrics['win_rate']:.1%})\n"
            f"Trades perdants: {metrics['losing_trades']}\n"
            f"Gain moyen: ${metrics['avg_profit']:.2f}\n"
            f"Perte moyenne: ${metrics['avg_loss']:.2f}\n"
            f"Ratio Sharpe: {metrics['sharpe_ratio']:.2f}"
        )
        
        plt.figtext(0.15, 0.02, summary_text, fontsize=9, ha='left')
        
        # Ajuster la mise en page
        plt.tight_layout(rect=[0, 0.05, 1, 0.95])
        
        # Titre général
        plt.suptitle(f"Résultats du Backtest ({self.start_date.date()} - {self.end_date.date()})", fontsize=16)
        
        # Sauvegarder le graphique
        plt.savefig(output_file, dpi=300)
        logger.info(f"Results plot saved to {output_file}")