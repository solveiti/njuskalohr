"""
Sentry initialization helper for njuskalohr scripts

This module provides a centralized Sentry initialization function
to be used across all scripts and the API.
"""

import os
import logging
from typing import Optional, List

try:
    import sentry_sdk
    from sentry_sdk.integrations.logging import LoggingIntegration
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.starlette import StarletteIntegration
    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False


def init_sentry(
    script_name: Optional[str] = None,
    integrations: Optional[List] = None,
    **kwargs
) -> bool:
    """
    Initialize Sentry with configuration from environment variables

    Args:
        script_name: Name of the script/service (for logging purposes)
        integrations: List of Sentry integrations to enable
        **kwargs: Additional arguments to pass to sentry_sdk.init()

    Returns:
        bool: True if Sentry was initialized, False otherwise

    Environment Variables:
        SENTRY_DSN: Sentry Data Source Name (required)
        SENTRY_ENVIRONMENT: Environment name (default: production)
        SENTRY_TRACES_SAMPLE_RATE: Traces sample rate 0.0-1.0 (default: 1.0)
        SENTRY_PROFILES_SAMPLE_RATE: Profiles sample rate 0.0-1.0 (default: 1.0)
    """
    if not SENTRY_AVAILABLE:
        if script_name:
            print(f"⚠️ [{script_name}] Sentry SDK not installed - error tracking disabled")
        return False

    dsn = os.getenv("SENTRY_DSN")
    if not dsn:
        if script_name:
            print(f"⚠️ [{script_name}] SENTRY_DSN not configured - error tracking disabled")
        return False

    # Default integrations for scripts
    if integrations is None:
        integrations = [
            LoggingIntegration(
                level=logging.INFO,
                event_level=logging.ERROR
            )
        ]

    # Default configuration
    config = {
        "dsn": dsn,
        "environment": os.getenv("SENTRY_ENVIRONMENT", "production"),
        "traces_sample_rate": float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "1.0")),
        "profiles_sample_rate": float(os.getenv("SENTRY_PROFILES_SAMPLE_RATE", "1.0")),
        "integrations": integrations,
        "auto_session_tracking": True,
        "enable_tracing": True,
    }

    # Merge with any provided kwargs
    config.update(kwargs)

    # Initialize Sentry
    sentry_sdk.init(**config)

    environment = config["environment"]
    if script_name:
        print(f"✅ [{script_name}] Sentry initialized for environment: {environment}")

    return True


def init_sentry_for_api() -> bool:
    """
    Initialize Sentry specifically for FastAPI applications

    Returns:
        bool: True if Sentry was initialized, False otherwise
    """
    if not SENTRY_AVAILABLE:
        return False

    integrations = [
        StarletteIntegration(transaction_style="endpoint"),
        FastApiIntegration(transaction_style="endpoint"),
        LoggingIntegration(
            level=logging.INFO,
            event_level=logging.ERROR
        )
    ]

    return init_sentry(
        script_name="API",
        integrations=integrations
    )


def capture_exception_with_context(
    exception: Exception,
    context: dict = None,
    tags: dict = None
) -> None:
    """
    Capture an exception with additional context and tags

    Args:
        exception: The exception to capture
        context: Additional context dictionary
        tags: Tags to add to the event
    """
    if not SENTRY_AVAILABLE:
        return

    if context:
        for key, value in context.items():
            sentry_sdk.set_context(key, value)

    if tags:
        for key, value in tags.items():
            sentry_sdk.set_tag(key, value)

    sentry_sdk.capture_exception(exception)


def capture_message_with_context(
    message: str,
    level: str = "info",
    context: dict = None,
    tags: dict = None
) -> None:
    """
    Capture a message with additional context and tags

    Args:
        message: The message to capture
        level: Message level (debug, info, warning, error, fatal)
        context: Additional context dictionary
        tags: Tags to add to the event
    """
    if not SENTRY_AVAILABLE:
        return

    if context:
        for key, value in context.items():
            sentry_sdk.set_context(key, value)

    if tags:
        for key, value in tags.items():
            sentry_sdk.set_tag(key, value)

    sentry_sdk.capture_message(message, level=level)


def set_user_context(user_uuid: str = None, email: str = None, **kwargs) -> None:
    """
    Set user context for Sentry events

    Args:
        user_uuid: User UUID
        email: User email
        **kwargs: Additional user attributes
    """
    if not SENTRY_AVAILABLE:
        return

    user_data = {}
    if user_uuid:
        user_data["id"] = user_uuid
    if email:
        user_data["email"] = email

    user_data.update(kwargs)

    sentry_sdk.set_user(user_data)


def start_transaction(op: str, name: str, **kwargs):
    """
    Start a Sentry transaction

    Args:
        op: Operation name (e.g., "script", "api_call", "ad_submission")
        name: Transaction name
        **kwargs: Additional transaction attributes

    Returns:
        Transaction context manager or None if Sentry not available
    """
    if not SENTRY_AVAILABLE:
        # Return a dummy context manager that does nothing
        from contextlib import nullcontext
        return nullcontext()

    return sentry_sdk.start_transaction(op=op, name=name, **kwargs)
