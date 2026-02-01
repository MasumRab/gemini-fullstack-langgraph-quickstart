"""Rate limiting and context window management for Gemini API.

This module provides utilities to stay within Gemini API rate limits:
- RPM (Requests Per Minute)
- TPM (Tokens Per Minute)
- RPD (Requests Per Day)
- Context window size limits
"""

import logging
import time
from collections import deque
from datetime import datetime
from functools import lru_cache
from threading import Lock
from typing import Dict
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

from agent.models import GEMINI_FLASH, GEMINI_FLASH_LITE, GEMINI_PRO

# Timezone for daily reset
PACIFIC_TZ = ZoneInfo("America/Los_Angeles")


# Gemini 2.5 Model Rate Limits (Free Tier)
RATE_LIMITS = {
    GEMINI_FLASH: {
        "rpm": 15,
        "tpm": 1_000_000,
        "rpd": 1_500,
        "max_tokens": 1_048_576,
        "max_output_tokens": 8_192,
    },
    GEMINI_FLASH_LITE: {
        "rpm": 15,
        "tpm": 1_000_000,
        "rpd": 1_500,
        "max_tokens": 1_048_576,
        "max_output_tokens": 8_192,
    },
    GEMINI_PRO: {
        "rpm": 10,  # Lower RPM for Pro
        "tpm": 1_000_000,
        "rpd": 1_000,  # Lower daily limit
        "max_tokens": 2_097_152,
        "max_output_tokens": 8_192,
    },
}


class RateLimiter:
    """Thread-safe rate limiter for Gemini API calls."""

    def __init__(self, model: str = GEMINI_FLASH):
        """Initialize rate limiter for a specific model.

        Args:
            model: Model name to get rate limits for
        """
        self.model = model
        self.limits = RATE_LIMITS.get(model, RATE_LIMITS[GEMINI_FLASH])

        # Thread-safe locks
        self._lock = Lock()

        # Request tracking
        self._requests_per_minute: deque = deque()
        self._requests_per_day: deque = deque()
        self._tokens_per_minute: deque = deque()

        # Daily reset tracking (Pacific Time)
        self._last_reset_date = datetime.now(PACIFIC_TZ).date()

        # ⚡ Bolt Optimization: Lazy cleanup timestamp
        # Only cleanup if we are close to the limit or periodically (e.g. every 1 second).
        # This prevents cleaning up on every single token estimation/check if calls are bursty.
        self._last_cleanup = 0.0

        logger.info(
            f"Initialized RateLimiter for {model}: RPM={self.limits['rpm']}, TPM={self.limits['tpm']}, RPD={self.limits['rpd']}"
        )

    def _cleanup_old_requests(self):
        """Remove requests older than tracking windows."""
        now = time.time()

        # ⚡ Bolt Optimization: Throttle cleanup
        # If less than 1 second passed since last cleanup, skip.
        # This drastically reduces lock contention and overhead in high-throughput scenarios.
        if now - self._last_cleanup < 1.0:
            return

        self._last_cleanup = now
        minute_ago = now - 60
        day_ago = now - 86400

        # Clean up minute window
        while self._requests_per_minute and self._requests_per_minute[0] < minute_ago:
            self._requests_per_minute.popleft()

        while self._tokens_per_minute and self._tokens_per_minute[0][0] < minute_ago:
            self._tokens_per_minute.popleft()

        # Clean up day window
        while self._requests_per_day and self._requests_per_day[0] < day_ago:
            self._requests_per_day.popleft()

    def _check_daily_reset(self):
        """Check if we need to reset daily counters (midnight Pacific time)."""
        now_pt = datetime.now(PACIFIC_TZ)
        if now_pt.date() > self._last_reset_date:
            self._requests_per_day.clear()
            self._last_reset_date = now_pt.date()
            logger.info(f"Daily quota reset for {self.model} (Pacific Time)")

    def wait_if_needed(self, estimated_tokens: int = 1000) -> float:
        """Wait if necessary to stay within rate limits.

        Args:
            estimated_tokens: Estimated tokens for this request

        Returns:
            Time waited in seconds
        """
        total_wait_time = 0.0

        while True:
            # Check limits inside lock
            should_wait = False
            time_to_wait = 0.0

            with self._lock:
                self._cleanup_old_requests()
                self._check_daily_reset()

                now = time.time()

                # Check RPM limit
                if len(self._requests_per_minute) >= self.limits["rpm"]:
                    oldest_request = self._requests_per_minute[0]
                    rpm_wait = 60 - (now - oldest_request)
                    if rpm_wait > 0:
                        time_to_wait = max(time_to_wait, rpm_wait)
                        should_wait = True

                # Check TPM limit
                current_tpm = sum(tokens for _, tokens in self._tokens_per_minute)
                if current_tpm + estimated_tokens > self.limits["tpm"]:
                    if self._tokens_per_minute:
                        oldest_time = self._tokens_per_minute[0][0]
                        tpm_wait = 60 - (now - oldest_time)
                        if tpm_wait > 0:
                            time_to_wait = max(time_to_wait, tpm_wait)
                            should_wait = True

                # Check RPD limit (Hard Fail)
                if len(self._requests_per_day) >= self.limits["rpd"]:
                    logger.error(
                        f"Daily request limit ({self.limits['rpd']}) reached for {self.model}!"
                    )
                    raise Exception(
                        f"Daily quota exceeded for {self.model}. Resets at midnight Pacific time."
                    )

                if not should_wait:
                    # Proceed: Record this request
                    current_time = time.time()
                    self._requests_per_minute.append(current_time)
                    self._requests_per_day.append(current_time)
                    self._tokens_per_minute.append((current_time, estimated_tokens))
                    return total_wait_time

            # 🛡️ Sentinel: Wait OUTSIDE the lock to prevent blocking other threads
            # This allows other threads to check limits/stats even while this one waits for a slot.
            if should_wait:
                logger.warning(
                    f"Rate limit reached for {self.model}. Waiting {time_to_wait:.2f}s"
                )
                time.sleep(time_to_wait)
                total_wait_time += time_to_wait
                # Loop back to check if we can proceed now

    def get_current_usage(self) -> Dict[str, int]:
        """Get current usage statistics.

        Returns:
            Dictionary with current RPM, TPM, and RPD usage
        """
        with self._lock:
            self._cleanup_old_requests()

            current_tpm = sum(tokens for _, tokens in self._tokens_per_minute)

            return {
                "rpm": len(self._requests_per_minute),
                "rpm_limit": self.limits["rpm"],
                "tpm": current_tpm,
                "tpm_limit": self.limits["tpm"],
                "rpd": len(self._requests_per_day),
                "rpd_limit": self.limits["rpd"],
            }

    def get_max_context_size(self) -> int:
        """Get maximum context window size for this model.

        Returns:
            Maximum tokens allowed (input + output)
        """
        return self.limits["max_tokens"]

    def get_max_output_tokens(self) -> int:
        """Get maximum output tokens for this model.

        Returns:
            Maximum output tokens allowed
        """
        return self.limits["max_output_tokens"]


class ContextWindowManager:
    """Manage context window sizes to stay within model limits."""

    def __init__(self, model: str = GEMINI_FLASH):
        """Initialize context window manager.

        Args:
            model: Model name to get limits for
        """
        self.model = model
        self.limits = RATE_LIMITS.get(model, RATE_LIMITS[GEMINI_FLASH])
        self.max_tokens = self.limits["max_tokens"]
        self.max_output_tokens = self.limits["max_output_tokens"]

        # Reserve tokens for output
        self.max_input_tokens = self.max_tokens - self.max_output_tokens

        logger.info(
            f"ContextWindowManager for {model}: max_input={self.max_input_tokens}, max_output={self.max_output_tokens}"
        )

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text.

        Uses rough approximation: 1 token ≈ 4 characters for English text.

        Args:
            text: Input text

        Returns:
            Estimated token count
        """
        # Rough estimation: 1 token ≈ 4 characters
        return len(text) // 4

    def truncate_to_fit(self, text: str, max_tokens: int | None = None) -> str:
        """Truncate text to fit within token limit.

        Args:
            text: Input text
            max_tokens: Maximum tokens (defaults to max_input_tokens)

        Returns:
            Truncated text
        """
        if max_tokens is None:
            max_tokens = self.max_input_tokens

        estimated = self.estimate_tokens(text)

        if estimated <= max_tokens:
            return text

        # Truncate to fit
        target_chars = max_tokens * 4
        truncated = text[:target_chars]

        logger.warning(f"Truncated text from ~{estimated} to ~{max_tokens} tokens")

        return truncated + "\n\n[... truncated to fit context window ...]"

    def split_into_chunks(
        self, text: str, chunk_size: int | None = None
    ) -> list[str]:
        """Split text into chunks that fit within context window.

        Args:
            text: Input text
            chunk_size: Size of each chunk in tokens (defaults to max_input_tokens)

        Returns:
            List of text chunks
        """
        if chunk_size is None:
            chunk_size = self.max_input_tokens

        estimated = self.estimate_tokens(text)

        if estimated <= chunk_size:
            return [text]

        # Split into chunks
        chars_per_chunk = chunk_size * 4
        chunks = []

        for i in range(0, len(text), chars_per_chunk):
            chunk = text[i : i + chars_per_chunk]
            chunks.append(chunk)

        logger.info(f"Split text into {len(chunks)} chunks (~{chunk_size} tokens each)")

        return chunks

    def validate_input_size(self, text: str, raise_error: bool = False) -> bool:
        """Validate that input text fits within context window.

        Args:
            text: Input text
            raise_error: Whether to raise exception if too large

        Returns:
            True if text fits, False otherwise

        Raises:
            ValueError: If text is too large and raise_error=True
        """
        estimated = self.estimate_tokens(text)

        if estimated > self.max_input_tokens:
            msg = f"Input text (~{estimated} tokens) exceeds max input size ({self.max_input_tokens} tokens)"
            logger.error(msg)

            if raise_error:
                raise ValueError(msg)

            return False

        return True


# Global rate limiters (one per model)
_rate_limiters: Dict[str, RateLimiter] = {}
_limiter_lock = Lock()


def get_rate_limiter(model: str) -> RateLimiter:
    """Get or create a rate limiter for a model.

    Args:
        model: Model name

    Returns:
        RateLimiter instance for the model
    """
    with _limiter_lock:
        if model not in _rate_limiters:
            _rate_limiters[model] = RateLimiter(model)
        return _rate_limiters[model]


# ⚡ Bolt Optimization: Cache ContextWindowManager
# Since this class is stateless (except for config) and logs on init,
# caching it prevents unnecessary object creation and log spam on every LLM call.
@lru_cache(maxsize=16)
def get_context_manager(model: str) -> ContextWindowManager:
    """Get a context window manager for a model.

    Args:
        model: Model name

    Returns:
        ContextWindowManager instance
    """
    return ContextWindowManager(model)
