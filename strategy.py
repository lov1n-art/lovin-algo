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
    Runs a backtest simulation with dual logic: standard breakout and gap-up
    opening range breakout.
    """
    logging.info(f"--- Running simulation for {stock_symbol} for the last {days} days ---")

    manual_breakout_level = config.BREAKOUT_LEVELS.get(stock_symbol)
    if not manual_breakout_level:
        logging.error(f"Breakout level not defined for {stock_symbol}. Cannot run.")
        return

    instrument_token = get_instrument_token(kite, stock_symbol)
    if not instrument_token:
        logging.error(f"Could not get instrument token for {stock_symbol}. Cannot run.")
        return

    # Fetch historical data for the entire period
    # We add one extra day to ensure we have previous day's candles for SL calculation
    df_full = get_historical_data(kite, instrument_token, config.CANDLE_INTERVAL, days=days + 1)
    if df_full.empty:
        logging.error(f"Could not fetch historical data for {stock_symbol}. Aborting.")
        return

    # Ensure 'date' is a datetime object
    df_full['date'] = pd.to_datetime(df_full['date'])

    # Group data by day
    daily_groups = df_full.groupby(df_full['date'].dt.date)
    unique_days = list(daily_groups.groups.keys())

    # We need at least two days to have a previous day for SL calculation
    if len(unique_days) < 2:
        logging.warning("Not enough historical data to run a meaningful simulation (need at least 2 days).")
        return

    # Iterate through each day, starting from the second day
    for day_index in range(1, len(unique_days)):
        current_day_date = unique_days[day_index]
        prev_day_date = unique_days[day_index - 1]

        df_today = daily_groups.get_group(current_day_date)
        df_prev_day = daily_groups.get_group(prev_day_date)

        # Combine previous day and current day for continuous SL calculation
        df_combined = pd.concat([df_prev_day, df_today]).reset_index(drop=True)

        logging.info(f"\n--- Processing Day: {current_day_date} ---")

        # --- Determine Strategy for the Day ---
        opening_candle = df_today.iloc[0]
        breakout_level_for_the_day = manual_breakout_level
        strategy_mode = "Standard Breakout"

        # Check for Gap-Up condition
        if opening_candle['open'] > manual_breakout_level:
            strategy_mode = "Opening Range Breakout (Gap-Up)"
            # Wait for the first 15 minutes (5 candles of 3-min)
            opening_range_candles = df_today[df_today['date'].dt.time < datetime.strptime("09:30", "%H:%M").time()]
            if len(opening_range_candles) >= 5:
                breakout_level_for_the_day = opening_range_candles['high'].max()
                logging.info(f"Gap-Up detected. New ORB level set to: {breakout_level_for_the_day:.2f}")
            else:
                logging.warning("Not enough candles for 15-min Opening Range. Skipping day.")
                continue

        logging.info(f"Mode for the day: {strategy_mode} | Level: {breakout_level_for_the_day:.2f}")

        position_taken_today = False
        square_off_time = datetime.strptime(config.SQUARE_OFF_TIME, "%H:%M").time()

        # Iterate through the candles of the current day
        for i in range(len(df_today)):
            if position_taken_today:
                break # Only one trade per day

            # The current candle in the context of the combined (prev + today) dataframe
            # This ensures we can always look back for SL calculation
            combined_df_index = len(df_prev_day) + i
            if combined_df_index < 2: # Need at least 2 previous candles
                continue

            current_candle = df_today.iloc[i]
            current_dataframe_slice = df_combined.iloc[:combined_df_index + 1]

            # Skip checks if in ORB mode and before 9:30 AM
            if strategy_mode == "Opening Range Breakout (Gap-Up)" and current_candle['date'].time() < datetime.strptime("09:30", "%H:%M").time():
                continue

            # --- ENTRY LOGIC ---
            breakout, breakout_idx = check_breakout(current_dataframe_slice, breakout_level_for_the_day)

            if breakout:
                entry_price = current_candle["close"]
                stoploss_price = calculate_stoploss(current_dataframe_slice, breakout_idx, entry_price)

                if not stoploss_price:
                    continue

                stoploss_distance = entry_price - stoploss_price
                if stoploss_distance <= 0:
                    logging.warning(f"[{current_candle['date']}] Invalid SL distance ({stoploss_distance:.2f}). Skipping trade.")
                    continue

                target_distance = 2 * stoploss_distance
                target_price = entry_price + target_distance
                position_size = calculate_position_size(stoploss_distance)

                if position_size > 0:
                    logging.info(f"--- TRADE SIGNAL on {current_candle['date']} ---")
                    logging.info(f"  Stock: {stock_symbol} ({strategy_mode})")
                    logging.info(f"  Entry: {entry_price:.2f}")
                    logging.info(f"  Stoploss: {stoploss_price:.2f} (Distance: {stoploss_distance:.2f})")
                    logging.info(f"  Target: {target_price:.2f} (Distance: {target_distance:.2f})")
                    logging.info(f"  Position Size: {position_size}")

                    position_taken_today = True # Simulate taking the position
                    # In a real scenario, you'd place an order and manage the position.
                    # We break here to simulate only one trade per day.
                    break

    logging.info(f"\n--- Simulation for {stock_symbol} finished ---")


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
