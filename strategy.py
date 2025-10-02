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
    """Initializes the Kite Connect client with increased timeout."""
    if not config.API_KEY or config.API_KEY == "your_api_key_here":
        from market_simulator import SimulatedKiteConnect
        logging.info("Using simulated market data (API credentials not found)")
        return SimulatedKiteConnect()
    
    try:
        # Initialize with increased timeout
        kite = KiteConnect(
            api_key=config.API_KEY,
            timeout=30  # Increased timeout to 30 seconds
        )
        
        # Check if we have a valid access token
        if config.ACCESS_TOKEN and config.ACCESS_TOKEN != "your_access_token_here":
            kite.set_access_token(config.ACCESS_TOKEN)
        else:
            # Get new access token
            login_url = kite.login_url()
            logging.info(f"Please visit this URL to login: {login_url}")
            request_token = input("Enter request token from redirect URL: ")
            
            data = kite.generate_session(request_token, api_secret=config.API_SECRET)
            access_token = data["access_token"]
            
            # Save new access token
            with open(".env", "w") as f:
                f.write(f"KITE_API_KEY={config.API_KEY}\n")
                f.write(f"KITE_API_SECRET={config.API_SECRET}\n")
                f.write(f"KITE_ACCESS_TOKEN={access_token}")
            
            kite.set_access_token(access_token)
        
        logging.info("Kite Connect client initialized successfully")
        return kite
        
    except Exception as e:
        logging.error(f"Error initializing Kite Connect client: {str(e)}")
        logging.info("Falling back to simulation mode")
        from market_simulator import SimulatedKiteConnect
        return SimulatedKiteConnect()


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


def check_breakout(df, breakout_level):
    """Checks for a long breakout condition."""
    if df.empty:
        return False, None
    last_candle = df.iloc[-1]
    if last_candle["close"] > breakout_level:
        logging.info(f"Breakout detected! Close: {last_candle['close']}, Level: {breakout_level}")
        return True, len(df) - 1
    return False, None


def calculate_stoploss(df, breakout_candle_index, entry_price):
    """Calculates the stoploss for a long position."""
    # Look at the two candles just before the breakout candle.
    # breakout_candle_index is the index of the breakout candle itself.
    # We need to look at indices breakout_candle_index-2 and breakout_candle_index-1.
    previous_two_candles = df.iloc[breakout_candle_index - 2 : breakout_candle_index]

    # Option 1: Lowest low of the two candles before the breakout.
    sl_price_candlestick = previous_two_candles["low"].min()

    # Option 2: 2% below the entry price.
    sl_price_percentage = entry_price * 0.98

    # The stoploss is the lower of these two values.
    final_sl = min(sl_price_candlestick, sl_price_percentage)

    # Ensure SL is below entry price for a long trade.
    if final_sl >= entry_price:
        logging.warning(f"Calculated SL ({final_sl}) is not below entry price ({entry_price}). Using 2% rule as fallback.")
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
    """Places a Bracket Order for a long position."""
    logging.info(f"Placing Bracket Order for {quantity} shares of {symbol}.")
    logging.info(f"  SL distance: {sl_distance:.2f}, Target distance: {target_distance:.2f}")
    try:
        order_id = kite.place_order(
            variety=kite.VARIETY_BO,
            exchange=kite.EXCHANGE_NSE,
            tradingsymbol=symbol,
            transaction_type=kite.TRANSACTION_TYPE_BUY,  # Long position
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
    """Squares off all open MIS positions."""
    logging.info("Squaring off all open positions...")
    try:
        positions = kite.positions().get("net", [])
        for pos in positions:
            if pos["quantity"] != 0 and pos["product"] == kite.PRODUCT_MIS:
                # For long positions, quantity is positive, so we sell.
                if pos["quantity"] > 0:
                    place_market_order(kite, pos["tradingsymbol"], "SELL", pos["quantity"])
                # As a safeguard for any stray short positions:
                elif pos["quantity"] < 0:
                    place_market_order(kite, pos["tradingsymbol"], "BUY", abs(pos["quantity"]))
        logging.info("All positions squared off.")
    except Exception as e:
        logging.error(f"Error squaring off positions: {e}")


def run_simulation(kite, stock_symbol, days=10):
    """
    Runs a backtest simulation for a single stock over a historical period.
    This provides a stable way to test the strategy logic candle by candle.
    """
    logging.info(f"--- Running simulation for {stock_symbol} for the last {days} days ---")

    breakout_level = config.BREAKOUT_LEVELS.get(stock_symbol)
    if not breakout_level:
        logging.error(f"Breakout level not defined for {stock_symbol}. Cannot run simulation.")
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
            breakout, breakout_idx = check_breakout(current_dataframe_slice, breakout_level)

            if breakout:
                entry_price = current_candle["close"]
                stoploss_price = calculate_stoploss(current_dataframe_slice, breakout_idx, entry_price)

                if not stoploss_price:
                    continue

                # For a long position, SL is below entry, so distance is positive
                stoploss_distance = entry_price - stoploss_price
                if stoploss_distance <= 0:
                    logging.warning(f"[{current_candle['date']}] Invalid SL distance ({stoploss_distance}). Skipping trade.")
                    continue

                # Target is 2x the risk (stoploss distance)
                target_distance = 2 * stoploss_distance
                target_price = entry_price + target_distance
                position_size = calculate_position_size(stoploss_distance)

                if position_size > 0:
                    logging.info(f"--- TRADE SIGNAL on {current_candle['date']} ---")
                    logging.info(f"  Stock: {stock_symbol}")
                    logging.info(f"  Entry: {entry_price:.2f}")
                    logging.info(f"  Stoploss: {stoploss_price:.2f} (Distance: {stoploss_distance:.2f})")
                    logging.info(f"  Target: {target_price:.2f} (Distance: {target_distance:.2f})")
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
