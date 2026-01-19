"""Tests for RateLimiter."""

import unittest
from datetime import datetime, timedelta

from agent.rate_limiter import PACIFIC_TZ, RateLimiter


class TestRateLimiter(unittest.TestCase):
    def test_daily_reset_logic(self):
        """Test that daily reset occurs at midnight Pacific Time."""
        limiter = RateLimiter()

        # Manually set last reset date to yesterday
        yesterday = datetime.now(PACIFIC_TZ).date() - timedelta(days=1)
        limiter._last_reset_date = yesterday

        # Add some dummy requests
        limiter._requests_per_day.append(12345)
        self.assertEqual(len(limiter._requests_per_day), 1)

        # Trigger reset check
        limiter._check_daily_reset()

        # Should be cleared
        self.assertEqual(len(limiter._requests_per_day), 0)
        self.assertEqual(limiter._last_reset_date, datetime.now(PACIFIC_TZ).date())

    def test_no_reset_same_day(self):
        """Test that daily reset does not occur on the same day."""
        limiter = RateLimiter()

        # Set last reset date to today
        today = datetime.now(PACIFIC_TZ).date()
        limiter._last_reset_date = today

        # Add some dummy requests
        limiter._requests_per_day.append(12345)
        self.assertEqual(len(limiter._requests_per_day), 1)

        # Trigger reset check
        limiter._check_daily_reset()

        # Should NOT be cleared
        self.assertEqual(len(limiter._requests_per_day), 1)
        self.assertEqual(limiter._last_reset_date, today)


if __name__ == "__main__":
    unittest.main()
