"""Tests for RateLimiter."""

import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from agent.rate_limiter import RateLimiter, PACIFIC_TZ

class TestRateLimiter(unittest.TestCase):
    @patch('agent.rate_limiter.datetime')
    def test_daily_reset_logic(self, mock_datetime):
        """Test that daily reset occurs at midnight Pacific Time."""
        # Setup mock time
        now_date = datetime(2023, 10, 2, 12, 0, 0, tzinfo=PACIFIC_TZ)
        mock_datetime.now.return_value = now_date

        limiter = RateLimiter()

        # Manually set last reset date to yesterday
        yesterday_date = now_date.date() - timedelta(days=1)
        limiter._last_reset_date = yesterday_date

        # Add some dummy requests
        limiter._requests_per_day.append(12345)
        self.assertEqual(len(limiter._requests_per_day), 1)

        # Trigger reset check
        limiter._check_daily_reset()

        # Should be cleared
        self.assertEqual(len(limiter._requests_per_day), 0)
        self.assertEqual(limiter._last_reset_date, now_date.date())

    @patch('agent.rate_limiter.datetime')
    def test_no_reset_same_day(self, mock_datetime):
        """Test that daily reset does not occur on the same day."""
        # Setup mock time
        now_date = datetime(2023, 10, 2, 12, 0, 0, tzinfo=PACIFIC_TZ)
        mock_datetime.now.return_value = now_date

        limiter = RateLimiter()

        # Set last reset date to today
        limiter._last_reset_date = now_date.date()

        # Add some dummy requests
        limiter._requests_per_day.append(12345)
        self.assertEqual(len(limiter._requests_per_day), 1)

        # Trigger reset check
        limiter._check_daily_reset()

        # Should NOT be cleared
        self.assertEqual(len(limiter._requests_per_day), 1)
        self.assertEqual(limiter._last_reset_date, now_date.date())

if __name__ == "__main__":
    unittest.main()
