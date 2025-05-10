# Robot Trader Crypto

Un système de trading automatisé pour les cryptomonnaies, basé sur une stratégie de scalping hybride avec gestion rigoureuse des risques.

## Table des matières

- [Présentation](#présentation)
- [Fonctionnalités](#fonctionnalités)
- [Installation](#installation)
- [Structure du projet](#structure-du-projet)
- [Utilisation](#utilisation)
  - [Configuration](#configuration)
  - [Mode Trading en direct](#mode-trading-en-direct)
  - [Mode Paper Trading](#mode-paper-trading)
  - [Backtesting](#backtesting)
  - [Optimisation](#optimisation)
  - [Interface graphique](#interface-graphique)
- [Tests sans API Binance](#tests-sans-api-binance)
- [Stratégie de trading](#stratégie-de-trading)
- [Gestion des risques](#gestion-des-risques)
- [Extension du projet](#extension-du-projet)
- [Avertissement](#avertissement)
- [Licence](#licence)

## Présentation

Ce robot trader a été conçu pour exploiter les opportunités de marché sur les plateformes de cryptomonnaies en utilisant une approche de scalping hybride. Il combine :

- **Analyse technique avancée** pour détecter les signaux d'entrée et de sortie
- **Analyse des tendances à moyen terme** pour filtrer les faux signaux
- **Gestion rigoureuse du risque** pour préserver le capital

Le système est entièrement modulaire, personnalisable et permet d'optimiser les paramètres grâce à des backtests sur données historiques.

## Fonctionnalités

- **Trading automatisé** : Exécution automatique des ordres selon la stratégie définie
- **Multi-Exchange** : Compatible avec Binance, FTX, Bybit et autres plateformes via ccxt
- **Gestion du risque avancée** : Stop-loss, take-profit échelonnés et trailing stops
- **Backtesting** : Test de stratégies sur données historiques
- **Optimisation** : Recherche des meilleurs paramètres pour maximiser la performance
- **Interface graphique** : Tableau de bord complet pour contrôler et surveiller le système
- **Mode simulation** : Possibilité de tester sans compte d'exchange réel

## Installation

### Prérequis

- Python 3.10 ou supérieur
- pip (gestionnaire de paquets Python)

### Installation des dépendances

```bash
# Cloner le dépôt
git clone https://github.com/votre-username/robot-trader-crypto.git
cd robot-trader-crypto

# Créer un environnement virtuel (recommandé)
python -m venv venv
source venv/bin/activate  # Sous Linux/Mac
# ou
venv\Scripts\activate.bat  # Sous Windows

# Installer les dépendances
pip install -r requirements.txt
```
