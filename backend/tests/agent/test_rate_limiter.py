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

    @patch("agent.rate_limiter.time")
    def test_wait_if_needed_rpm_limit(self, mock_time):
        """Test waiting when RPM limit is hit."""
        limiter = RateLimiter()
        # Set strict limits for testing
        limiter.limits = {"rpm": 1, "tpm": 1000, "rpd": 100}

        # Initial time
        start_time = 1000.0
        mock_time.time.return_value = start_time

        # 1. First request - should pass immediately
        limiter.wait_if_needed(10)
        mock_time.sleep.assert_not_called()
        self.assertEqual(len(limiter._requests_per_minute), 1)

        # 2. Second request - should trigger wait
        # Logic flow:
        # Loop 1:
        #   time() -> 1000.0
        #   cleanup() -> no change (diff < 1.0 or just no old reqs)
        #   check limit -> RPM=1, limit=1. Full.
        #   wait = 60 - (1000 - 1000) = 60.
        #   sleep(60)
        # Loop 2:
        #   time() -> 1061.0
        #   cleanup() -> removes old request (1000.0 < 1061-60)
        #   check limit -> RPM=0. OK.
        #   add request at 1061.0

        # We need side_effect for time.time() to simulate time passing.
        # The implementation calls time.time() multiple times:
        # 1. _cleanup_old_requests check
        # 2. main limit check
        # 3. recording timestamp (on success)

        # Iteration 1 (Fail/Wait):
        # 1. cleanup check -> 1000.0
        # 2. limit check -> 1000.0 -> WAIT

        # Iteration 2 (Success):
        # 3. cleanup check -> 1061.0
        # 4. limit check -> 1061.0
        # 5. record -> 1061.0

        mock_time.time.side_effect = [
            start_time, start_time,             # Iteration 1
            start_time + 61.0, start_time + 61.0, start_time + 61.0  # Iteration 2
        ]

        limiter.wait_if_needed(10)

        mock_time.sleep.assert_called_once_with(60.0)
        # After success, we added the new request at 1061, old one removed
        self.assertEqual(len(limiter._requests_per_minute), 1)
        self.assertEqual(limiter._requests_per_minute[0], 1061.0)

if __name__ == "__main__":
    unittest.main()
