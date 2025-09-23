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
    if breakout_candle_index < 2:
        logging.warning("Not enough data to calculate stoploss based on previous candles.")
        return entry_price * 1.02  # Default to 2% SL

    # Option 1: High of the last 2 candles *before* the breakout candle
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


def run_strategy(kite):
    """Runs the main trading strategy loop."""
    traded_stocks = set()
    while True:
        # Check for square-off time
        now = datetime.now()
        square_off_time = datetime.strptime(config.SQUARE_OFF_TIME, "%H:%M").time()
        if now.time() >= square_off_time:
            square_off_all_positions(kite)
            logging.info("End of trading day. Exiting strategy.")
            break

        for stock_symbol in config.STOCKS:
            if stock_symbol in traded_stocks:
                continue

            support_level = config.SUPPORT_LEVELS.get(stock_symbol)
            if not support_level:
                logging.warning(f"Support level not defined for {stock_symbol}. Skipping.")
                continue

            instrument_token = get_instrument_token(kite, stock_symbol)
            if not instrument_token:
                logging.warning(f"Could not get instrument token for {stock_symbol}. Skipping.")
                continue

            df = get_historical_data(kite, instrument_token, config.CANDLE_INTERVAL)
            breakout, breakout_idx = check_breakout(df, support_level)

            if breakout:
                entry_price = df.iloc[breakout_idx]["close"]
                stoploss_price = calculate_stoploss(df, breakout_idx, entry_price)

                if not stoploss_price:
                    continue

                stoploss_distance = stoploss_price - entry_price
                target_price = entry_price - (2 * stoploss_distance)

                position_size = calculate_position_size(stoploss_distance)

                if position_size > 0:
                    logging.info(f"Trade signal for {stock_symbol}:")
                    logging.info(f"  Entry: {entry_price:.2f}")
                    logging.info(f"  Stoploss: {stoploss_price:.2f}")
                    logging.info(f"  Target: {target_price:.2f}")
                    logging.info(f"  Position Size: {position_size}")

                    # Place Bracket Order
                    target_distance = 2 * stoploss_distance
                    order_placed = place_bracket_order(
                        kite,
                        stock_symbol,
                        position_size,
                        stoploss_distance,
                        target_distance
                    )

                    if order_placed:
                        traded_stocks.add(stock_symbol)

        logging.info("Waiting for the next candle...")
        time.sleep(180)  # Wait for 3 minutes


if __name__ == "__main__":
    kite_client = initialize_kite_client()
    if kite_client:
        logging.info("Successfully created a Kite Connect client instance.")
        # The user needs to uncomment the following lines and provide a valid access token
        # kite_client.set_access_token(config.ACCESS_TOKEN)

        # Uncomment the line below to run the strategy
        # run_strategy(kite_client)
