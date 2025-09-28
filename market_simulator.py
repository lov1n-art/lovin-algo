# -*- coding: utf-8 -*-
"""
Market data simulation for testing without live API access.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

class SimulatedKiteConnect:
    """Simulates KiteConnect API behavior for testing."""
    
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.VARIETY_REGULAR = "regular"
        self.EXCHANGE_NSE = "NSE"
        self.TRANSACTION_TYPE_SELL = "SELL"
        self.TRANSACTION_TYPE_BUY = "BUY"
        self.PRODUCT_MIS = "MIS"
        self.ORDER_TYPE_MARKET = "MARKET"
        self.ORDER_TYPE_SL = "SL"
        
    def instruments(self, exchange):
        """Simulate instruments data."""
        sample_instruments = [
            {
                "instrument_token": 408065,
                "tradingsymbol": "INFY",
                "exchange": "NSE"
            },
            {
                "instrument_token": 738561,
                "tradingsymbol": "RELIANCE",
                "exchange": "NSE"
            },
            {
                "instrument_token": 2953217,
                "tradingsymbol": "TCS",
                "exchange": "NSE"
            }
        ]
        return sample_instruments

    def _generate_simulated_data(self, instrument_token, from_date, to_date, interval):
        """Generate simulated OHLCV data."""
        # Set random seed based on instrument token for consistent simulation
        np.random.seed(instrument_token)
        
        # Generate dates
        dates = pd.date_range(start=from_date, end=to_date, freq='3min')
        dates = dates[dates.indexer_between_time('9:15', '15:30')]
        
        # Base price depends on instrument (to make it realistic)
        base_price = instrument_token % 1000 * 100  # Simple way to get different price ranges
        
        # Generate prices
        prices = np.random.normal(loc=base_price, scale=base_price*0.02, size=len(dates))
        daily_trend = np.linspace(-5, 5, len(dates))  # Add a slight trend
        prices = prices + daily_trend
        
        # Create OHLCV data
        data = []
        for i, date in enumerate(dates):
            price = prices[i]
            candle = {
                "date": date,
                "open": price * (1 + np.random.normal(0, 0.001)),
                "high": price * (1 + abs(np.random.normal(0, 0.002))),
                "low": price * (1 - abs(np.random.normal(0, 0.002))),
                "close": price * (1 + np.random.normal(0, 0.001)),
                "volume": int(np.random.normal(100000, 20000))
            }
            data.append(candle)
        
        return data

    def historical_data(self, instrument_token, from_date, to_date, interval):
        """Simulate historical data."""
        data = self._generate_simulated_data(instrument_token, from_date, to_date, interval)
        return data

    def place_order(self, variety, exchange, tradingsymbol, transaction_type, 
                   quantity, product, order_type, trigger_price=None):
        """Simulate order placement."""
        order_id = f"simulated_order_{np.random.randint(10000, 99999)}"
        logging.info(f"Simulated order placed: {order_id} for {tradingsymbol}")
        return order_id