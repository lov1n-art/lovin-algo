# -*- coding: utf-8 -*-
"""
Configuration for the trading strategy.
"""

# Zerodha API credentials
# It's recommended to use environment variables for these
API_KEY = "YOUR_API_KEY"
API_SECRET = "YOUR_API_SECRET"
ACCESS_TOKEN = "YOUR_ACCESS_TOKEN"

# Strategy parameters
STOCKS = ["INFY", "RELIANCE", "TCS"]  # Example stock symbols (NSE)
RESISTANCE_LEVELS = {
    "INFY": 1600,
    "RELIANCE": 2600,
    "TCS": 3600,
}  # Manually marked resistance levels for long breakouts
RISK_PER_TRADE = 1000  # in INR
SQUARE_OFF_TIME = "23:59"  # Extended for testing
CANDLE_INTERVAL = "3minute"

# Safety Mode Configuration
SAFETY_MODE = True  # Set to False to enable real trading
MAX_TRADES_PER_DAY = 3  # Maximum number of trades per day
MAX_LOSS_PER_DAY = 3000  # Maximum loss per day in INR
