"""
Sentry initialization helper for njuskalohr scripts
"""

import os
import logging
from typing import Optional, List

try:
    import sentry_sdk
    from sentry_sdk.integrations.logging import LoggingIntegration
    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False


def init_sentry(script_name: Optional[str] = None) -> bool:
    """
    Initialize Sentry with configuration from environment variables.

    Environment Variables:
        SENTRY_DSN: Sentry Data Source Name (required)
        SENTRY_ENVIRONMENT: Environment name (default: production)
        SENTRY_TRACES_SAMPLE_RATE: Traces sample rate 0.0-1.0 (default: 1.0)
    """
    if not SENTRY_AVAILABLE:
        return False

    dsn = os.getenv("SENTRY_DSN")
    if not dsn:
        return False

    sentry_sdk.init(
        dsn=dsn,
        environment=os.getenv("SENTRY_ENVIRONMENT", "production"),
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "1.0")),
        integrations=[
            LoggingIntegration(level=logging.INFO, event_level=logging.ERROR)
        ],
        auto_session_tracking=True,
        enable_tracing=True,
    )

    if script_name:
        print(f"✅ [{script_name}] Sentry initialized")

    return True
