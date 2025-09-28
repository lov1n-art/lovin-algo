#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Main script to run the intraday breakout strategy.
"""

import logging
from datetime import datetime
import time
from strategy import (
    initialize_kite_client,
    get_instrument_token,
    get_historical_data,
    check_breakout,
    calculate_stoploss,
)
from order_manager import OrderManager, calculate_position_size
import config

def main():
    # Initialize logging with more detailed format
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logging.info("Starting breakout strategy monitoring...")
    
    # Initialize Kite client
    kite = initialize_kite_client()
    if not kite:
        logging.error("Failed to initialize Kite client. Exiting.")
        return
        
    # Initialize order manager
    order_manager = OrderManager(kite)
    
    # Log safety mode status
    if config.SAFETY_MODE:
        logging.info("Running in SAFETY MODE - No real trades will be placed")
    else:
        logging.warning("Running in LIVE MODE - Real trades will be placed!")

    while True:
        current_time = datetime.now().strftime("%H:%M")
        
        # Exit if it's past square off time
        if current_time >= config.SQUARE_OFF_TIME:
            logging.info("Reached square off time. Exiting.")
            break

        # Check each stock for breakout
        for symbol in config.STOCKS:
            try:
                logging.info(f"Checking {symbol} for breakout conditions...")
                # Get instrument token
                token = get_instrument_token(kite, symbol)
                if not token:
                    logging.error(f"Could not find instrument token for {symbol}")
                    continue
                logging.info(f"Analyzing {symbol} (Token: {token})")

                # Get historical data
                df = get_historical_data(
                    kite,
                    token,
                    config.CANDLE_INTERVAL,
                    days=1
                )

                # Check for breakout
                support_level = config.SUPPORT_LEVELS.get(symbol)
                is_breakout, breakout_idx = check_breakout(df, support_level)

                if is_breakout:
                    logging.info(f"Breakout detected in {symbol}")
                    entry_price = df.iloc[-1]["close"]
                    stoploss = calculate_stoploss(df, breakout_idx, entry_price)
                    quantity = calculate_position_size(entry_price, stoploss)
                    
                    if quantity > 0:
                        order_manager.place_order(symbol, quantity, entry_price, stoploss)
                    else:
                        logging.warning(f"Invalid position size calculated for {symbol}")

            except Exception as e:
                logging.error(f"Error processing {symbol}: {e}")

        # Wait for next candle
        logging.info("Waiting 60 seconds before next check...")
        time.sleep(60)  # Adjust sleep time based on your candle interval

if __name__ == "__main__":
    main()