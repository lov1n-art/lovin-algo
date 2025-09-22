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
SUPPORT_LEVELS = {
    "INFY": 1500,
    "RELIANCE": 2500,
    "TCS": 3500,
}  # Manually marked support levels
RISK_PER_TRADE = 1000  # in INR
SQUARE_OFF_TIME = "15:15"  # 3:15 PM
CANDLE_INTERVAL = "3minute"
