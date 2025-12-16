
import unittest
from unittest.mock import patch, MagicMock
from agent.rate_limiter import get_rate_limiter, get_context_manager, RATE_LIMITS
from agent.models import GEMMA_2_27B_IT, GEMMA_3_27B_IT, GEMINI_FLASH

class TestRateLimiterGemma(unittest.TestCase):
    def test_gemma_rate_limits_exist(self):
        """Verify Gemma models are in RATE_LIMITS with correct values."""
        self.assertIn(GEMMA_2_27B_IT, RATE_LIMITS)
        self.assertIn(GEMMA_3_27B_IT, RATE_LIMITS)

        # Check context limits
        self.assertEqual(RATE_LIMITS[GEMMA_2_27B_IT]["max_tokens"], 8192)
        self.assertEqual(RATE_LIMITS[GEMMA_3_27B_IT]["max_tokens"], 8192)

        # Check defaults vs Gemma
        self.assertNotEqual(RATE_LIMITS[GEMMA_2_27B_IT]["max_tokens"], RATE_LIMITS[GEMINI_FLASH]["max_tokens"])

    def test_context_manager_truncation_gemma(self):
        """Verify ContextManager truncates correctly for Gemma."""
        cm = get_context_manager(GEMMA_2_27B_IT)

        # 8192 tokens * 4 chars/token = 32768 chars (approx)
        # Create a string that exceeds this
        long_text = "a" * 40000

        truncated = cm.truncate_to_fit(long_text)

        # Should be truncated
        self.assertLess(len(truncated), 40000)
        self.assertTrue(truncated.endswith("[... truncated to fit context window ...]"))

        # Verify it respects the smaller limit
        estimated_tokens = cm.estimate_tokens(truncated)
        self.assertLessEqual(estimated_tokens, 8192)

    def test_rate_limiter_instantiation(self):
        """Verify rate limiter picks up correct limits."""
        rl = get_rate_limiter(GEMMA_2_27B_IT)
        self.assertEqual(rl.limits["max_tokens"], 8192)
