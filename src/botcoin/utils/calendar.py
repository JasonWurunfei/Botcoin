"""This module contains utility functions for working with market calendars."""

from datetime import datetime, date

import pandas_market_calendars as mcal


def is_market_open(exchange: str, date: datetime) -> bool:
    """
    Check if the market is open for the given exchange on a specific date.

    Args:
        exchange (str): The market exchange identifier (e.g., 'NYSE', 'NASDAQ').
        date (datetime): The date to check.

    Returns:
        bool: True if the market is open, False otherwise.
    """
    calendar = mcal.get_calendar(exchange)
    schedule = calendar.schedule(start_date=date.date(), end_date=date.date())
    return (
        not schedule.empty
        and schedule.iloc[0]["market_open"] <= date <= schedule.iloc[0]["market_close"]
    )


def is_market_open_now(exchange: str) -> bool:
    """
    Check if the market is currently open for the given exchange.

    Args:
        exchange (str): The market exchange identifier (e.g., 'NYSE', 'NASDAQ').

    Returns:
        bool: True if the market is currently open, False otherwise.
    """
    calendar = mcal.get_calendar(exchange)
    now = datetime.now(calendar.tz)
    schedule = calendar.schedule(start_date=now.date(), end_date=now.date())
    return (
        not schedule.empty
        and schedule.iloc[0]["market_open"] <= now <= schedule.iloc[0]["market_close"]
    )


def is_market_open_today(exchange: str) -> bool:
    """
    Check if the market is open today for the given exchange.

    Args:
        exchange (str): The market exchange identifier (e.g., 'NYSE', 'NASDAQ').

    Returns:
        bool: True if the market is open today, False otherwise.
    """
    calendar = mcal.get_calendar(exchange)
    today = datetime.now(calendar.tz).date()
    schedule = calendar.schedule(start_date=today, end_date=today)
    return not schedule.empty


def is_market_open_on_date(exchange: str, d: date) -> bool:
    """
    Check if the market is open on a specific date for the given exchange.

    Args:
        exchange (str): The market exchange identifier (e.g., 'NYSE', 'NASDAQ').
        d (date): The date to check.
    Returns:
        bool: True if the market is open on the specified date, False otherwise.
    """
    calendar = mcal.get_calendar(exchange)
    schedule = calendar.schedule(start_date=d, end_date=d)
    return not schedule.empty
