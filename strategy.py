# -*- coding: utf-8 -*-
"""
Main script for the short-only intraday breakout strategy.
"""

from kiteconnect import KiteConnect
import config
import logging
import pandas as pd
from datetime import datetime, timedelta
import time
logging.basicConfig(level=logging.INFO)

# A global variable to cache instruments
INSTRUMENTS = None


def initialize_kite_client():
    """Initializes the Kite Connect client."""
    try:
        kite = KiteConnect(api_key=config.API_KEY)
        # The following line is commented out as it requires a valid access token.
        # kite.set_access_token(config.ACCESS_TOKEN)
        logging.info("Kite Connect client initialized successfully.")
        return kite
    except Exception as e:
        logging.error(f"Error initializing Kite Connect client: {e}")
        return None


def get_instruments(kite, exchange="NSE"):
    """Fetches and caches instruments."""
    global INSTRUMENTS
    if INSTRUMENTS is None:
        try:
            INSTRUMENTS = kite.instruments(exchange)
            logging.info(f"Successfully fetched instruments for {exchange}.")
        except Exception as e:
            logging.error(f"Error fetching instruments: {e}")
            return None
    return INSTRUMENTS


def get_instrument_token(kite, symbol, exchange="NSE"):
    """Gets the instrument token for a given stock symbol."""
    instruments = get_instruments(kite, exchange)
    if instruments:
        for instrument in instruments:
            if instrument["tradingsymbol"] == symbol:
                return instrument["instrument_token"]
    return None


def get_historical_data(kite, instrument_token, interval, days=5):
    """Fetches historical data for a given instrument token."""
    to_date = datetime.now().date()
    from_date = to_date - timedelta(days=days)
    try:
        records = kite.historical_data(instrument_token, from_date, to_date, interval)
        return pd.DataFrame(records)
    except Exception as e:
        logging.error(f"Error fetching historical data for token {instrument_token}: {e}")
        return pd.DataFrame()


def check_breakout(df, support_level):
    """Checks for a breakout condition."""
    if df.empty:
        return False, None
    last_candle = df.iloc[-1]
    if last_candle["close"] < support_level:
        logging.info(f"Breakout detected! Close: {last_candle['close']}, Support: {support_level}")
        return True, len(df) - 1
    return False, None


def calculate_stoploss(df, breakout_candle_index, entry_price):
    """Calculates the stoploss for a short position."""
    # With the new simulation loop, breakout_candle_index will always be >= 2,
    # so we can safely look back at the previous two candles.

    # Option 1: High of the last 2 candles *before* the breakout candle
    # This will now correctly use the previous day's candle if the breakout
    # happens early in the current day's session.
    sl_price_candlestick = df["high"].iloc[breakout_candle_index - 2 : breakout_candle_index].max()

    # Option 2: 2% of the stock price
    sl_price_percentage = entry_price * 1.02

    # For a short position, the stoploss is above the entry price.
    # "Whichever is lower" means a tighter stoploss.
    final_sl = min(sl_price_candlestick, sl_price_percentage)

    # Ensure SL is above entry price
    if final_sl <= entry_price:
        logging.warning(f"Calculated SL ({final_sl}) is not above entry price ({entry_price}). Using 2% rule as fallback.")
        return sl_price_percentage

    return final_sl


def calculate_position_size(stoploss_distance):
    """Calculates the position size."""
    if stoploss_distance <= 0:
        return 0
    return round(config.RISK_PER_TRADE / stoploss_distance)


def place_market_order(kite, symbol, action, quantity):
    """Places a simple market order."""
    logging.info(f"Placing {action} market order for {quantity} shares of {symbol}.")
    try:
        order_id = kite.place_order(
            variety=kite.VARIETY_REGULAR,
            exchange=kite.EXCHANGE_NSE,
            tradingsymbol=symbol,
            transaction_type=action,
            quantity=quantity,
            product=kite.PRODUCT_MIS,
            order_type=kite.ORDER_TYPE_MARKET,
        )
        logging.info(f"Market order placed successfully. Order ID: {order_id}")
        return order_id
    except Exception as e:
        logging.error(f"Error placing market order for {symbol}: {e}")
        return None


def place_bracket_order(kite, symbol, quantity, sl_distance, target_distance):
    """Places a Bracket Order for a short position."""
    logging.info(f"Placing Bracket Order for {quantity} shares of {symbol}.")
    logging.info(f"  SL distance: {sl_distance:.2f}, Target distance: {target_distance:.2f}")
    try:
        order_id = kite.place_order(
            variety=kite.VARIETY_BO,
            exchange=kite.EXCHANGE_NSE,
            tradingsymbol=symbol,
            transaction_type=kite.TRANSACTION_TYPE_SELL, # Short position
            quantity=quantity,
            product=kite.PRODUCT_MIS,
            order_type=kite.ORDER_TYPE_MARKET,
            stoploss=round(sl_distance, 2),
            squareoff=round(target_distance, 2)
        )
        logging.info(f"Bracket Order placed successfully. Order ID: {order_id}")
        return order_id
    except Exception as e:
        logging.error(f"Error placing Bracket Order for {symbol}: {e}")
        return None


def square_off_all_positions(kite):
    """Squares off all open positions."""
    logging.info("Squaring off all open positions...")
    try:
        positions = kite.positions().get("net", [])
        for pos in positions:
            if pos["quantity"] != 0 and pos["product"] == kite.PRODUCT_MIS:
                # For short positions, quantity is negative
                if pos["quantity"] < 0:
                    place_market_order(kite, pos["tradingsymbol"], "BUY", abs(pos["quantity"]))
                # The strategy is short-only, but as a safeguard:
                elif pos["quantity"] > 0:
                    place_market_order(kite, pos["tradingsymbol"], "SELL", pos["quantity"])
        logging.info("All positions squared off.")
    except Exception as e:
        logging.error(f"Error squaring off positions: {e}")


def run_simulation(kite, stock_symbol, days=10):
    """
    Runs a backtest simulation for a single stock over a historical period.
    This provides a stable way to test the strategy logic candle by candle.
    """
    logging.info(f"--- Running simulation for {stock_symbol} for the last {days} days ---")

    support_level = config.SUPPORT_LEVELS.get(stock_symbol)
    if not support_level:
        logging.error(f"Support level not defined for {stock_symbol}. Cannot run simulation.")
        return

    instrument_token = get_instrument_token(kite, stock_symbol)
    if not instrument_token:
        logging.error(f"Could not get instrument token for {stock_symbol}. Cannot run simulation.")
        return

    df = get_historical_data(kite, instrument_token, config.CANDLE_INTERVAL, days=days)
    if df.empty:
        logging.error(f"Could not fetch historical data for {stock_symbol}. Aborting.")
        return

    position = None
    square_off_time = datetime.strptime(config.SQUARE_OFF_TIME, "%H:%M").time()

    # Loop through each candle of the historical data as if it's a live feed
    for i in range(2, len(df)):
        current_candle = df.iloc[i]
        current_dataframe_slice = df.iloc[0:i+1] # Data up to the current candle

        # --- POSITION MANAGEMENT ---
        if position:
            # Check for square-off time
            if current_candle["date"].time() >= square_off_time:
                logging.info(f"[{current_candle['date']}] Squaring off position in {stock_symbol} due to EOD.")
                position = None # Simulate closing the position
                continue # Move to the next day

            # In a real backtest, you would check for SL/TP hits here.
            # For this simulation, we focus on the entry logic.

        # --- ENTRY LOGIC ---
        if not position: # Only check for entries if we don't have a position
            breakout, breakout_idx = check_breakout(current_dataframe_slice, support_level)

            if breakout:
                entry_price = current_candle["close"]
                stoploss_price = calculate_stoploss(current_dataframe_slice, breakout_idx, entry_price)

                if not stoploss_price:
                    continue

                stoploss_distance = stoploss_price - entry_price
                if stoploss_distance <= 0:
                    logging.warning(f"[{current_candle['date']}] Invalid SL distance ({stoploss_distance}). Skipping trade.")
                    continue

                target_price = entry_price - (2 * stoploss_distance)
                position_size = calculate_position_size(stoploss_distance)

                if position_size > 0:
                    logging.info(f"--- TRADE SIGNAL on {current_candle['date']} ---")
                    logging.info(f"  Stock: {stock_symbol}")
                    logging.info(f"  Entry: {entry_price:.2f}")
                    logging.info(f"  Stoploss: {stoploss_price:.2f} (Distance: {stoploss_distance:.2f})")
                    logging.info(f"  Target: {target_price:.2f}")
                    logging.info(f"  Position Size: {position_size}")

                    # Simulate taking a position
                    position = {
                        "symbol": stock_symbol,
                        "entry_price": entry_price,
                        "sl": stoploss_price,
                        "tp": target_price,
                        "size": position_size
                    }
                    # In a real scenario, you would place the bracket order here
                    # For simulation, we just log and move on.
                    # We break here to not take another trade on the same stock in the simulation
                    break

    logging.info(f"--- Simulation for {stock_symbol} finished ---")


if __name__ == "__main__":
    # This main block is for demonstration and simulation purposes.
    # It will run the simulation for the first stock in the config file.
    kite_client = initialize_kite_client()
    if kite_client:
        logging.info("Successfully created a Kite Connect client instance.")
        # The user needs to provide a valid access token for the simulation
        # to fetch historical data.
        try:
            # This is a placeholder for a valid access token for demonstration.
            # In a real scenario, the user would generate this token daily.
            kite_client.set_access_token("YOUR_ACCESS_TOKEN_HERE")

            # Run simulation for the first stock in the list
            if config.STOCKS:
                run_simulation(kite_client, config.STOCKS[0])
            else:
                logging.warning("No stocks found in config.py to run simulation.")

        except Exception as e:
            logging.error(f"Could not run simulation. Please ensure your API credentials and access token are valid. Error: {e}")
