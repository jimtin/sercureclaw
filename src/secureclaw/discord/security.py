"""Discord rate limiting and security utilities."""

import time
from collections import defaultdict
from dataclasses import dataclass, field

from secureclaw.config import get_settings
from secureclaw.logging import get_logger

log = get_logger("secureclaw.discord.security")


@dataclass
class RateLimitState:
    """Track rate limit state for a user."""

    message_timestamps: list[float] = field(default_factory=list)
    last_warning: float = 0.0


class RateLimiter:
    """Rate limiter for Discord messages."""

    def __init__(
        self,
        max_messages: int = 10,
        window_seconds: float = 60.0,
        warning_cooldown: float = 30.0,
    ) -> None:
        """Initialize rate limiter.

        Args:
            max_messages: Maximum messages allowed per window.
            window_seconds: Time window in seconds.
            warning_cooldown: Minimum time between warnings.
        """
        self._max_messages = max_messages
        self._window_seconds = window_seconds
        self._warning_cooldown = warning_cooldown
        self._states: dict[int, RateLimitState] = defaultdict(RateLimitState)

    def check(self, user_id: int) -> tuple[bool, str | None]:
        """Check if a user is rate limited.

        Args:
            user_id: The Discord user ID.

        Returns:
            Tuple of (is_allowed, warning_message).
        """
        now = time.time()
        state = self._states[user_id]

        # Clean old timestamps
        state.message_timestamps = [
            ts for ts in state.message_timestamps if now - ts < self._window_seconds
        ]

        # Check limit
        if len(state.message_timestamps) >= self._max_messages:
            warning = None
            if now - state.last_warning > self._warning_cooldown:
                warning = (
                    f"You're sending messages too quickly. "
                    f"Please wait a moment before trying again."
                )
                state.last_warning = now
            return False, warning

        # Record this message
        state.message_timestamps.append(now)
        return True, None


class UserAllowlist:
    """Manage allowed Discord users."""

    def __init__(self) -> None:
        """Initialize the allowlist."""
        settings = get_settings()
        self._allowed_ids: set[int] = set(settings.allowed_user_ids)
        self._allow_all = len(self._allowed_ids) == 0

        if self._allow_all:
            log.warning(
                "allowlist_empty",
                message="No allowed users configured, allowing all users",
            )
        else:
            log.info("allowlist_configured", count=len(self._allowed_ids))

    def is_allowed(self, user_id: int) -> bool:
        """Check if a user is allowed.

        Args:
            user_id: The Discord user ID.

        Returns:
            True if allowed, False otherwise.
        """
        if self._allow_all:
            return True
        return user_id in self._allowed_ids

    def add(self, user_id: int) -> None:
        """Add a user to the allowlist.

        Args:
            user_id: The Discord user ID to add.
        """
        self._allowed_ids.add(user_id)
        self._allow_all = False
        log.info("user_added_to_allowlist", user_id=user_id)

    def remove(self, user_id: int) -> None:
        """Remove a user from the allowlist.

        Args:
            user_id: The Discord user ID to remove.
        """
        self._allowed_ids.discard(user_id)
        log.info("user_removed_from_allowlist", user_id=user_id)


def detect_prompt_injection(content: str) -> bool:
    """Basic detection of common prompt injection patterns.

    Args:
        content: The message content to check.

    Returns:
        True if potential injection detected, False otherwise.
    """
    # Convert to lowercase for checking
    lower_content = content.lower()

    # Common injection patterns
    injection_patterns = [
        "ignore previous instructions",
        "ignore all previous",
        "disregard your instructions",
        "forget your instructions",
        "you are now",
        "act as if",
        "pretend you are",
        "new instructions:",
        "system prompt:",
        "override:",
        "jailbreak",
        "dan mode",
        "developer mode enable",
    ]

    for pattern in injection_patterns:
        if pattern in lower_content:
            log.warning(
                "potential_prompt_injection_detected",
                pattern=pattern,
                content_preview=content[:100],
            )
            return True

    return False
