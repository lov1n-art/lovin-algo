# -*- coding: utf-8 -*-
"""
Order management module for the trading strategy.
"""

import logging
import config
from datetime import datetime

def calculate_position_size(entry_price, stoploss):
    """Calculate the position size based on risk per trade."""
    if entry_price <= 0 or stoploss <= 0:
        return 0
        
    risk_per_share = abs(entry_price - stoploss)  # For long positions
    if risk_per_share <= 0:
        return 0
        
    shares = config.RISK_PER_TRADE / risk_per_share
    return int(shares)  # Round down to nearest whole number

class OrderManager:
    def __init__(self, kite):
        self.kite = kite
        self.daily_trade_count = 0
        self.daily_pnl = 0
        self.open_positions = {}
        
    def can_place_trade(self):
        """Check if we can place a new trade based on safety parameters."""
        if config.SAFETY_MODE:
            logging.info("Safety mode is ON - No real trades will be placed")
            return False
            
        # Check daily trade limit
        if self.daily_trade_count >= config.MAX_TRADES_PER_DAY:
            logging.warning("Daily trade limit reached")
            return False
            
        # Check daily loss limit
        if self.daily_pnl <= -config.MAX_LOSS_PER_DAY:
            logging.warning("Daily loss limit reached")
            return False
            
        return True
        
    def place_order(self, symbol, quantity, entry_price, stoploss):
        """Place a new long order with stoploss."""
        if not self.can_place_trade():
            logging.info(f"Trade signal for {symbol} - Entry: {entry_price}, SL: {stoploss} (SIMULATION ONLY)")
            return False
            
        try:
            # Place the main long order
            order_id = self.kite.place_order(
                variety=self.kite.VARIETY_REGULAR,
                exchange=self.kite.EXCHANGE_NSE,
                tradingsymbol=symbol,
                transaction_type=self.kite.TRANSACTION_TYPE_BUY,  # Changed to BUY for long positions
                quantity=quantity,
                product=self.kite.PRODUCT_MIS,
                order_type=self.kite.ORDER_TYPE_MARKET
            )
            
            # Place the stoploss order
            sl_order_id = self.kite.place_order(
                variety=self.kite.VARIETY_REGULAR,
                exchange=self.kite.EXCHANGE_NSE,
                tradingsymbol=symbol,
                transaction_type=self.kite.TRANSACTION_TYPE_SELL,  # Changed to SELL for long positions
                quantity=quantity,
                product=self.kite.PRODUCT_MIS,
                order_type=self.kite.ORDER_TYPE_SL,
                trigger_price=stoploss
            )
            
            self.daily_trade_count += 1
            self.open_positions[symbol] = {
                'quantity': quantity,
                'entry_price': entry_price,
                'stoploss': stoploss,
                'order_id': order_id,
                'sl_order_id': sl_order_id
            }
            
            logging.info(f"Orders placed for {symbol} - Entry: {entry_price}, SL: {stoploss}")
            return True
            
        except Exception as e:
            logging.error(f"Error placing orders for {symbol}: {e}")
            return False
            
    def square_off_all_positions(self):
        """Square off all open positions."""
        if config.SAFETY_MODE:
            logging.info("Safety mode is ON - No real square-off needed")
            return
            
        for symbol, position in self.open_positions.items():
            try:
                self.kite.place_order(
                    variety=self.kite.VARIETY_REGULAR,
                    exchange=self.kite.EXCHANGE_NSE,
                    tradingsymbol=symbol,
                    transaction_type=self.kite.TRANSACTION_TYPE_SELL,  # Changed to SELL for long positions
                    quantity=position['quantity'],
                    product=self.kite.PRODUCT_MIS,
                    order_type=self.kite.ORDER_TYPE_MARKET
                )
                logging.info(f"Squared off position in {symbol}")
            except Exception as e:
                logging.error(f"Error squaring off {symbol}: {e}")