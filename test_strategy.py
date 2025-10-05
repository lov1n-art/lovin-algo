# -*- coding: utf-8 -*-
"""
Unit tests for the dual-mode trading strategy.
"""

import unittest
import pandas as pd
from strategy import (
    check_breakout,
    calculate_stoploss,
    calculate_position_size,
    run_simulation,
)
import config
from unittest.mock import MagicMock, patch

class TestDualModeStrategy(unittest.TestCase):
    """Tests the core logic for both standard and gap-up ORB modes."""

    def setUp(self):
        """Set up common test data."""
        self.breakout_level = 1000
        config.BREAKOUT_LEVELS = {"TEST": self.breakout_level}
        config.STOCKS = ["TEST"]

        # --- Data for a Standard Breakout Day ---
        # Previous day's data for SL calculation
        prev_day_standard = pd.DataFrame({
            'date': pd.to_datetime(['2023-01-01 15:24:00', '2023-01-01 15:27:00']),
            'open': [990, 992], 'high': [993, 994], 'low': [989, 991], 'close': [992, 993]
        })
        # Today's data: opens below level, then breaks out
        today_standard = pd.DataFrame({
            'date': pd.to_datetime([
                '2023-01-02 09:15:00', '2023-01-02 09:18:00', '2023-01-02 09:21:00',
                '2023-01-02 09:24:00' # Breakout candle
            ]),
            'open':  [995, 996, 998, 1001],
            'high':  [997, 998, 1000, 1004],
            'low':   [994, 995, 997, 1000],
            'close': [996, 997, 999, 1002] # Close > 1000
        })
        self.standard_day_data = pd.concat([prev_day_standard, today_standard], ignore_index=True)

        # --- Data for a Gap-Up ORB Day ---
        # Previous day's data
        prev_day_gapup = pd.DataFrame({
            'date': pd.to_datetime(['2023-01-03 15:24:00', '2023-01-03 15:27:00']),
            'open': [980, 982], 'high': [983, 984], 'low': [979, 981], 'close': [982, 983]
        })
        # Today's data: Gaps up above 1000, forms a 15-min range, then breaks out
        today_gapup = pd.DataFrame({
            'date': pd.to_datetime([
                # Opening Range (9:15 to 9:27) -> High is 1015
                '2023-01-04 09:15:00', '2023-01-04 09:18:00', '2023-01-04 09:21:00',
                '2023-01-04 09:24:00', '2023-01-04 09:27:00',
                # Post-ORB consolidation
                '2023-01-04 09:30:00', '2023-01-04 09:33:00',
                # Breakout of ORB high
                '2023-01-04 09:36:00'
            ]),
            'open':  [1010, 1012, 1011, 1013, 1014, 1012, 1013, 1016],
            'high':  [1012, 1014, 1013, 1015, 1014, 1014, 1015, 1018], # ORB High = 1015
            'low':   [1009, 1010, 1010, 1012, 1011, 1011, 1012, 1015],
            'close': [1011, 1013, 1012, 1014, 1013, 1013, 1014, 1017] # Close > 1015
        })
        self.gap_up_day_data = pd.concat([prev_day_gapup, today_gapup], ignore_index=True)

    @patch('strategy.get_instrument_token')
    @patch('strategy.get_historical_data')
    @patch('strategy.logging')
    def test_standard_breakout_day(self, mock_logging, mock_get_historical_data, mock_get_instrument_token):
        """Verify that a standard breakout above the manual level is triggered."""
        mock_get_historical_data.return_value = self.standard_day_data
        mock_get_instrument_token.return_value = 12345  # Dummy token

        mock_kite = MagicMock()
        run_simulation(mock_kite, "TEST", days=1)

        log_calls = [call[0][0] for call in mock_logging.info.call_args_list]
        self.assertIn("Mode for the day: Standard Breakout | Level: 1000.00", log_calls)
        trade_signal_found = any("--- TRADE SIGNAL" in call for call in log_calls)
        self.assertTrue(trade_signal_found, "Trade signal for standard breakout was not logged.")

    @patch('strategy.get_instrument_token')
    @patch('strategy.get_historical_data')
    @patch('strategy.logging')
    def test_gap_up_orb_day(self, mock_logging, mock_get_historical_data, mock_get_instrument_token):
        """Verify that a gap-up switches to ORB and triggers on the new level."""
        mock_get_historical_data.return_value = self.gap_up_day_data
        mock_get_instrument_token.return_value = 12345  # Dummy token

        mock_kite = MagicMock()
        run_simulation(mock_kite, "TEST", days=1)

        log_calls = [call[0][0] for call in mock_logging.info.call_args_list]
        self.assertIn("Gap-Up detected. New ORB level set to: 1015.00", log_calls)
        self.assertIn("Mode for the day: Opening Range Breakout (Gap-Up) | Level: 1015.00", log_calls)
        trade_signal_found = any("--- TRADE SIGNAL" in call for call in log_calls)
        self.assertTrue(trade_signal_found, "Trade signal for ORB breakout was not logged.")
        trade_log_found = any("(Opening Range Breakout (Gap-Up))" in call for call in log_calls)
        self.assertTrue(trade_log_found, "The trade log did not specify it was an ORB trade.")

    def test_calculate_stoploss_long(self):
        """Test the stoploss calculation for a long position."""
        # Using the standard day data for a concrete SL calculation example
        # Breakout at index 5 (close=1002), so we look at candles at index 3 and 4.
        # Lows are 995 and 997. The min is 995.
        entry_price = 1002
        breakout_idx = 5 # Index in the combined (prev_day + today) dataframe

        # Low of last 2 candles before breakout (index 3 and 4) is 995
        sl_candlestick = 995
        # 2% SL is 1002 * 0.98 = 981.96
        sl_percentage = 981.96

        # The lower of the two is 981.96
        expected_sl = min(sl_candlestick, sl_percentage)
        self.assertAlmostEqual(expected_sl, 981.96)

        sl = calculate_stoploss(self.standard_day_data, breakout_idx, entry_price)
        self.assertAlmostEqual(sl, expected_sl)

if __name__ == "__main__":
    unittest.main()