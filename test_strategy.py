# -*- coding: utf-8 -*-
"""
Unit tests for the trading strategy logic.
"""

import unittest
import pandas as pd
from strategy import (
    check_breakout,
    calculate_stoploss,
    calculate_position_size,
)
import config

class TestStrategyLogic(unittest.TestCase):
    """Tests the core logic of the trading strategy."""

    def setUp(self):
        """Set up test data."""
        self.sample_data_breakout = pd.DataFrame({
            "date": pd.to_datetime(["2023-01-01 09:15:00", "2023-01-01 09:18:00", "2023-01-01 09:21:00", "2023-01-01 09:24:00"]),
            "open": [105, 106, 107, 102],
            "high": [107, 108, 108, 103],
            "low": [104, 105, 106, 98],
            "close": [106, 107, 102, 99],
        })
        self.sample_data_no_breakout = pd.DataFrame({
            "date": pd.to_datetime(["2023-01-01 09:15:00", "2023-01-01 09:18:00", "2023-01-01 09:21:00"]),
            "open": [105, 106, 107],
            "high": [107, 108, 108],
            "low": [104, 105, 106],
            "close": [106, 107, 108],
        })
        self.support_level = 100

    def test_check_breakout(self):
        """Test the breakout detection logic."""
        is_breakout, idx = check_breakout(self.sample_data_breakout, self.support_level)
        self.assertTrue(is_breakout)
        self.assertEqual(idx, 3)

        is_breakout, _ = check_breakout(self.sample_data_no_breakout, self.support_level)
        self.assertFalse(is_breakout)

    def test_calculate_stoploss(self):
        """Test the stoploss calculation."""
        # Breakout at index 3, entry price is 99
        entry_price = 99
        breakout_idx = 3

        # High of last 2 candles before breakout (index 1 and 2) is 108
        # 2% SL is 99 * 1.02 = 100.98
        # The lower of the two is 100.98
        sl = calculate_stoploss(self.sample_data_breakout, breakout_idx, entry_price)
        self.assertAlmostEqual(sl, 100.98)

        # Test with insufficient data
        sl_insufficient = calculate_stoploss(self.sample_data_breakout.iloc[:1], 0, 105)
        self.assertAlmostEqual(sl_insufficient, 105 * 1.02)

    def test_calculate_position_size(self):
        """Test the position size calculation."""
        # Risk: 1000, SL distance: 5
        size = calculate_position_size(5)
        self.assertEqual(size, 200)

        # Risk: 1000, SL distance: 10
        size = calculate_position_size(10)
        self.assertEqual(size, 100)

        # Zero SL distance
        size_zero_sl = calculate_position_size(0)
        self.assertEqual(size_zero_sl, 0)


if __name__ == "__main__":
    unittest.main()
