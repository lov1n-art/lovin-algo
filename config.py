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
STOCKS = ["YATHARTH", "ADITYA", "ASAHIINDIA", "NETWEB", "HBLPOWER", "ASKAUTO", "ANANDRATHI", 
          "MARUTI", "GABRIEL", "KIOCL", "SYRMA", "EICHERMOT", "JSWSTEEL", "NSLNISP", 
          "JAYNECOIND", "HEROMOTOCO", "MINDACORP", "IMFA", "SHAILY", "HYUNDAI", 
          "INOXGREEN", "ASHOKLEY", "LT"]  # NSE symbols

SUPPORT_LEVELS = {
    "YATHARTH": 746.5,      # Yatharth Hospital & Trauma Care Services
    "ADITYA": 540.25,       # Aditya Vision
    "ASAHIINDIA": 865.8,    # Asahi India Glass
    "NETWEB": 3531.6,       # Netweb Technologies
    "HBLPOWER": 806.5,      # HBL Engineering
    "ASKAUTO": 538.35,      # ASK Automotive
    "ANANDRATHI": 2760.20,  # Anand Rathi
    "MARUTI": 15951.88,     # Maruti Suzuki
    "GABRIEL": 1214.2,      # Gabriel India
    "KIOCL": 430.22,        # KIOCL Limited
    "SYRMA": 791.5,         # Syrma SGS
    "EICHERMOT": 6969.27,   # Eicher Motors
    "JSWSTEEL": 1119.70,    # JSW Steel
    "NSLNISP": 44.35,       # NSLNISP
    "JAYNECOIND": 67.91,    # Jay Bharat Maruti
    "HEROMOTOCO": 5269.50,  # Hero MotoCorp
    "MINDACORP": 565.10,    # Minda Corporation
    "IMFA": 1114.65,        # Indian Metals & Ferro Alloys
    "SHAILY": 2220.30,      # Shaily Engineering
    "HYUNDAI": 2634.8,      # Hyundai Motor India
    "INOXGREEN": 205.5,     # INOX Green Energy
    "ASHOKLEY": 141.33,     # Ashok Leyland
    "LT": 3679.6,           # Larsen & Toubro
    "ETERNAL": 324.25       # ETERNAL
}  # Support levels

# Target parameters
REWARD_RISK_RATIO = 2  # Target will be 2 times the risk (1:2 risk-reward)
TARGET_PERCENTAGES = {
    "TARGET": {"percent": 1.0, "quantity": 1.0}  # Single target at 2x risk distance
}
RISK_PER_TRADE = 100  # in INR
SQUARE_OFF_TIME = "15:15"  # Temporary extended time for testing
CANDLE_INTERVAL = "3minute"  # 3-minute candles

# Safety Mode Configuration
SAFETY_MODE = True  # Set to False to enable real trading
MAX_TRADES_PER_DAY = 10  # Maximum number of trades per day
MAX_LOSS_PER_DAY = 1000  # Maximum loss per day in INR
