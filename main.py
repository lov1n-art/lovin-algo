#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Main script to run the intraday breakout strategy.
"""

import logging
from datetime import datetime
import time

# Set to keep track of stocks already traded today
traded_stocks = set()

def reset_daily_trades():
    """Reset the traded stocks set at the start of each trading day."""
    global traded_stocks
    if traded_stocks:
        logging.info(f"Resetting daily trade tracking. Previously traded today: {', '.join(traded_stocks)}")
    traded_stocks.clear()
    logging.info("Daily trade tracking reset - Ready for new trading day")
from strategy import (
    initialize_kite_client,
    get_instrument_token,
    get_historical_data,
    check_breakout,
    calculate_stoploss_and_targets,
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
        
        # Reset traded stocks at the start of each day
        if current_time == "09:15":
            reset_daily_trades()
            logging.info("=== Starting new trading day ===")
            logging.info(f"Monitoring {len(config.STOCKS)} stocks for breakout opportunities")
            logging.info("Remember: Only one trade per stock allowed per day")
        
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
                    logging.error(f"Skipping {symbol} - Could not find instrument token")
                    continue
                
                logging.info(f"Processing {symbol} with token {token}")

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
                    if symbol in traded_stocks:
                        logging.info(f"⚠️ Breakout detected in {symbol} but SKIPPING - Already traded today")
                        logging.info(f"   Strategy allows only one trade per stock per day")
                        continue
                        
                    logging.info(f"Breakout detected in {symbol}")
                    entry_price = df.iloc[-1]["close"]
                    stoploss, targets = calculate_stoploss_and_targets(df, breakout_idx, entry_price)
                    quantity = calculate_position_size(entry_price, stoploss)
                    
                    if quantity > 0:
                        logging.info(f"Taking trade in {symbol}:")
                        logging.info(f"  Support Level: {support_level}")
                        logging.info(f"  Breakout Price: {entry_price}")
                        logging.info(f"  Position Size: {quantity} shares")
                        logging.info(f"  Total Position Value: {quantity * entry_price:.2f}")
                        
                        # Calculate target price based on risk-reward ratio
                        risk = entry_price - stoploss
                        target_price = entry_price + (risk * config.REWARD_RISK_RATIO)
                        targets = {"TARGET": {"price": target_price, "quantity": quantity}}

                        if order_manager.place_order(symbol, quantity, entry_price, stoploss, targets):
                            traded_stocks.add(symbol)
                            logging.info(f"Added {symbol} to today's traded stocks - no more trades for this stock today")
                    else:
                        logging.warning(f"Invalid position size calculated for {symbol}")
                elif is_breakout and symbol in traded_stocks:
                    logging.info(f"Breakout detected in {symbol} but skipping as it was already traded today.")

            except Exception as e:
                logging.error(f"Error processing {symbol}: {e}")

        # Wait for next candle
        logging.info(f"Waiting {config.CANDLE_INTERVAL} seconds before next check...")
        time.sleep(180)  # Using candle interval from config

if __name__ == "__main__":
    main()