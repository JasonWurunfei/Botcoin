"""This module contains exceptions related to data processing in the Botcoin application."""


class DataRetrievalError(RuntimeError):
    """Exception raised when there is an error retrieving data."""

    def __init__(self, message: str):
        super().__init__(message)


class YfDataRetrievalError(DataRetrievalError):
    """Exception raised when there is an error retrieving data from Yahoo Finance."""
