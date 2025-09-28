# -*- coding: utf-8 -*-
"""
Configuration for the trading strategy.
"""

from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Zerodha API credentials
API_KEY = os.getenv("KITE_API_KEY")
API_SECRET = os.getenv("KITE_API_SECRET")
ACCESS_TOKEN = os.getenv("KITE_ACCESS_TOKEN")

# Strategy parameters
STOCKS = ["INFY", "RELIANCE", "TCS", "LT"]  # Example stock symbols (NSE)
SUPPORT_LEVELS = {
    "INFY": 1500,
    "RELIANCE": 2500,
    "TCS": 3500,
    "LT": 1800
}  # Manually marked support levels
RISK_PER_TRADE = 1000  # in INR
SQUARE_OFF_TIME = "23:59"  # Temporary extended time for testing
CANDLE_INTERVAL = "3minute"

# Safety Mode Configuration
SAFETY_MODE = True  # Set to False to enable real trading
MAX_TRADES_PER_DAY = 100  # Maximum number of trades per day
MAX_LOSS_PER_DAY = 100000  # Maximum loss per day in INR
