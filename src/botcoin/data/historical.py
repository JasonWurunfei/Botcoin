"""This module is used to fetch historical and real-time data for stock symbols."""

from abc import ABC, abstractmethod
from enum import Enum
import os
from datetime import datetime, timedelta, date
from typing import override, Optional

import pytz
import pandas as pd
import yfinance as yf
from dotenv import load_dotenv

from botcoin.exceptions.data import YfDataRetrievalError
from botcoin.utils.calendar import is_market_open_today
from botcoin.utils.log import logging


# Load variables from .env file into environment
load_dotenv()


class TimeGranularity(Enum):
    """
    Enum for time granularity options.
    """

    ONE_MINUTE = "1m"
    TWO_MINUTES = "2m"
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    THIRTY_MINUTES = "30m"
    SIXTY_MINUTES = "60m"
    NINETY_MINUTES = "90m"
    ONE_HOUR = "1h"
    ONE_DAY = "1d"
    FIVE_DAYS = "5d"
    ONE_WEEK = "1wk"
    ONE_MONTH = "1mo"
    THREE_MONTHS = "3mo"


class DataProvider(ABC):
    """
    Abstract base class for data providers.
    This class defines the interface for fetching historical data.
    """

    @abstractmethod
    def get_ohlcv(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        granularity: TimeGranularity,
    ) -> pd.DataFrame:
        """
        Fetches historical data for the specified date range.

        Args:
            symbol (str): The stock ticker symbol.
            start_date (date): Start date for the data request.
            end_date (date): End date for the data request.
            granularity (TimeGranularity): The time granularity for the data.

        Returns:
            pd.DataFrame: DataFrame containing the historical data.
            format: {datetime: [open, high, low, close, volume]}
        """

    def get_ohlcv_1min(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> pd.DataFrame:
        """
        Fetches historical data for the specified date range with a default granularity of 1 minute.

        Args:
            symbol (str): The stock ticker symbol.
            start_date (date): Start date for the data request.
            end_date (date): End date for the data request.

        Returns:
            pd.DataFrame: DataFrame containing the historical data.
            format: {datetime: [open, high, low, close, volume]}
        """
        return self.get_ohlcv(symbol, start_date, end_date, TimeGranularity.ONE_MINUTE)


class YfDataProvider(DataProvider):
    """
    A concrete implementation of DataProvider that uses Yahoo Finance to fetch data.
    """

    def __init__(self, tz: str = "US/Eastern"):
        """
        Initializes the YfDataProvider with a timezone.

        Args:
            tz (str): The timezone to use for the data. Default is "US/Eastern".
        """
        self.tz = pytz.timezone(tz)

    def get_ohlcv(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        granularity: TimeGranularity,
    ) -> pd.DataFrame:
        # Fetch data from yfinance

        # Ensure the start is before the end
        if start_date > end_date:
            raise ValueError("Start date must be before end date.")

        # Set the start and end time to be before and after the market hours
        start = str(start_date)
        end = str(end_date)

        df = yf.download(
            tickers=symbol,
            start=start,
            end=end,
            interval=granularity.value,
            multi_level_index=False,
            progress=False,  # Disable progress bar
        )

        if df is not None and not df.empty:
            df.index = pd.to_datetime(df.index).tz_convert(self.tz)
        else:
            raise YfDataRetrievalError(
                f"Failed to retrieve data for {symbol} from {start} to {end} with"
                + f" granularity {granularity.value}."
            )

        return df


class DataManager:
    """
    A class to manage and fetch historical data for stock symbols.

    It stores data locally to avoid repeated requests for the same data.
    When new data is fetched, it merges it with existing local data.
    If there is a gap between the last local data time interval and the
    new data, it will fill that gap with the new data to make sure the local
    data is always continuous.
    """

    logger = logging.getLogger(__qualname__)

    def __init__(
        self,
        dp: DataProvider,
        data_folder: Optional[str] = None,
        tz: str = "US/Eastern",
    ):
        self.dp = dp
        self.data_folder = data_folder or os.getenv("DATA_FOLDER", "data")
        self.tz = pytz.timezone(tz)

        # Ensure the data folder exists
        if not os.path.exists(self.data_folder):
            os.makedirs(self.data_folder)

    def get_ohlcv_1min(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> pd.DataFrame:
        """
        Fetches historical data for the specified date range with a granularity of 1 minute.
        Args:
            symbol (str): The stock ticker symbol.
            start_date (date): Start date for the data request.
            end_date (date): End date for the data request. Not inclusive.
        Returns:
            pd.DataFrame: DataFrame containing the historical data.
            format: {datetime: [open, high, low, close, volume]}
        """
        return self.get_ohlcv(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            granularity=TimeGranularity.ONE_MINUTE,
        )

    def get_ohlcv(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        granularity: TimeGranularity,
    ) -> pd.DataFrame:
        """
        Fetches historical data for the specified date range with a given granularity.

        Args:
            symbol (str): The stock ticker symbol.
            start_date (date): Start date for the data request.
            end_date (date): End date for the data request. Not inclusive.
            granularity (TimeGranularity): The time granularity for the data.

        Returns:
            pd.DataFrame: DataFrame containing the historical data.
            format: {datetime: [open, high, low, close, volume]}
        """

        if start_date + timedelta(days=1) > end_date:
            raise ValueError("The date range must be at least 1 day.")

        df = self._get_local_data(symbol, granularity)
        if self._is_in_local(df, start_date, end_date):
            self.logger.debug("Retrieving data from local storage.")
            dt_start = datetime.combine(start_date, datetime.min.time())
            dt_end = datetime.combine(end_date, datetime.min.time())
            dt_start = self.tz.localize(dt_start)
            dt_end = self.tz.localize(dt_end)
            return df[(df.index >= dt_start) & (df.index <= dt_end)]

        # It's not in local storage, so we need to fetch it.

        # If the local data is empty, fetch new data
        if df.empty:
            self.logger.debug("Local data is empty, fetching new data.")
            new_df = self.dp.get_ohlcv(symbol, start_date, end_date, granularity)
            self._save_local_data(new_df, symbol, granularity)
            return new_df

        local_start_date, local_end_date = self._get_date_range(df)

        # fetch new data and merge it with the local data
        self.logger.debug("Fetching new data and merging with local data.")
        res_df = df.copy()
        if (
            start_date + timedelta(days=1) < end_date
        ):  # query for more than a single day
            if start_date >= local_end_date:
                # If the start date is after the last local data, fetch new data
                new_df = self.dp.get_ohlcv(
                    symbol, local_end_date, end_date, granularity
                )
                res_df = pd.concat([df, new_df])
                self._save_local_data(res_df, symbol, granularity)

            if end_date <= local_start_date:
                # If the end date is before the first local data, fetch new data
                new_df = self.dp.get_ohlcv(
                    symbol, start_date, local_start_date, granularity
                )
                res_df = pd.concat([new_df, df])
                self._save_local_data(res_df, symbol, granularity)

            if start_date < local_start_date <= end_date <= local_end_date:
                # If the start is before the local data and end is within the local data
                new_df = self.dp.get_ohlcv(
                    symbol, start_date, local_start_date, granularity
                )
                res_df = pd.concat([new_df, df])
                self._save_local_data(res_df, symbol, granularity)

            if local_start_date <= start_date < local_end_date < end_date:
                # If the start is after the local data and end is beyond the local data
                new_df = self.dp.get_ohlcv(
                    symbol, local_end_date, end_date, granularity
                )
                res_df = pd.concat([df, new_df])
                self._save_local_data(res_df, symbol, granularity)

            if start_date < local_start_date and end_date > local_end_date:
                # If the requested range is wider than the local data, fetch new data
                new_df_left = self.dp.get_ohlcv(
                    symbol, start_date, local_start_date, granularity
                )
                new_df_right = self.dp.get_ohlcv(
                    symbol, local_end_date, end_date, granularity
                )
                res_df = pd.concat([new_df_left, df, new_df_right])
                self._save_local_data(res_df, symbol, granularity)

        else:  # query for a single day
            if start_date < local_start_date:
                # If the start date is before the first local data, fetch new data
                new_df = self.dp.get_ohlcv(
                    symbol, start_date, local_start_date, granularity
                )
                res_df = pd.concat([new_df, df])
                self._save_local_data(res_df, symbol, granularity)

            if start_date >= local_end_date:
                # If the end date is after the last local data, fetch new data
                new_df = self.dp.get_ohlcv(
                    symbol, local_end_date, end_date, granularity
                )
                res_df = pd.concat([df, new_df])
                self._save_local_data(res_df, symbol, granularity)

        return res_df

    def _get_local_data(
        self, symbol: str, granularity: TimeGranularity
    ) -> pd.DataFrame:
        """
        Gets the data from local storage.

        Args:
            symbol (str): The stock ticker symbol.
            granularity (TimeGranularity): The time granularity for the data.

        Returns:
            pd.DataFrame: DataFrame containing the local data.
        """
        data_path = self._get_local_data_path(symbol, granularity)
        if os.path.exists(data_path):
            df = pd.read_parquet(data_path)
            df.index = pd.to_datetime(df.index).tz_convert(self.tz)
            return df
        return pd.DataFrame()

    def _save_local_data(
        self, df: pd.DataFrame, symbol: str, granularity: TimeGranularity
    ) -> None:
        """
        Saves the DataFrame to local storage.

        Args:
            df (pd.DataFrame): DataFrame containing the data to be saved.
            symbol (str): The stock ticker symbol.
            granularity (TimeGranularity): The time granularity for the data.
        """
        data_path = self._get_local_data_path(symbol, granularity)
        df.to_parquet(data_path)
        self.logger.info("Data saved to %s", data_path)

    def _get_local_data_path(self, symbol: str, granularity: TimeGranularity) -> str:
        """
        Returns the local file path where the data for the symbol is stored.

        Args:
            symbol (str): The stock ticker symbol.
            granularity (TimeGranularity): The time granularity for the data.

        Returns:
            str: Local path to the data file.
        """
        return os.path.join(
            self.data_folder, f"{symbol}_ohlcv_{granularity.value}.parquet"
        )

    def _is_in_local(
        self,
        df: pd.DataFrame,
        start_date: date,
        end_date: date,
    ) -> bool:
        """
        Checks if the requested date range is already in the local data.

        The data is always stored in units of 1 day, so only the start and end dates are checked.

        Args:
            df (pd.DataFrame): DataFrame containing the local data.
            start (date): Start date for the data request.
            end (date): End date for the data request.

        Returns:
            bool: True if the data exists in local storage, False otherwise.
        """
        if df.empty:
            return False

        local_start_date, local_end_date = self._get_date_range(df)

        if local_start_date <= start_date and local_end_date >= end_date:
            return True
        return False

    def _get_date_range(self, df: pd.DataFrame) -> tuple[date, date]:
        """
        Gets the local date range for the given DataFrame.

        Args:
            df (pd.DataFrame): The DataFrame containing the local data.

        Returns:
            tuple[date, date]: A tuple containing the start and end dates of the local data.
        """
        start = df.index.min()
        end = df.index.max()

        start_date = start.date()
        end_date = end.date() + timedelta(days=1)  # Include the end date in the range

        return start_date, end_date

    def get_current_data_date_range(
        self, symbol: str, granularity: TimeGranularity
    ) -> tuple[date, date]:
        """
        Gets the current date range for the given symbol and granularity.

        Args:
            symbol (str): The stock ticker symbol.
            granularity (TimeGranularity): The time granularity for the data.

        Returns:
            tuple[date, date]: A tuple containing the start and end dates of the current data.
        """
        df = self._get_local_data(symbol, granularity)
        return self._get_date_range(df)


class YfDataManager(DataManager):
    """
    A concrete implementation of DataManager that uses Yahoo Finance to fetch data.
    """

    def __init__(self, data_folder: str = "data", tz: str = "US/Eastern"):
        super().__init__(dp=YfDataProvider(), data_folder=data_folder, tz=tz)

    def _get_1min_data_range(self, symbol: str) -> tuple[date, date]:
        """
        Gets the 1 minute data range for the given symbol.

        Args:
            symbol (str): The stock ticker symbol.

        Returns:
            tuple[date, date]: A tuple containing the start and end dates of the 1 minute data.
        """
        return self.get_current_data_date_range(symbol, TimeGranularity.ONE_MINUTE)

    def _is_local_1min_data_beyond_30_days(self, symbol: str) -> bool:
        """
        Checks if the local 1 minute data for the given symbol is beyond 30 days.

        Args:
            symbol (str): The stock ticker symbol.
            granularity (TimeGranularity): The time granularity for the data.

        Returns:
            bool: True if the local data is beyond 30 days, False otherwise.
        """
        _, end_date = self._get_1min_data_range(symbol)
        today = date.today()
        if today - end_date > timedelta(days=30):
            return True
        return False

    @override
    def get_ohlcv_1min(
        self, symbol: str, start_date: date, end_date: date
    ) -> pd.DataFrame:
        """
        Downloads 1 minute data for the given symbol to local storage.

        Args:
            symbol (str): The stock ticker symbol.
            start_date (date): Start date for the data request.
            end_date (date): End date for the data request.

        Returns:
            pd.DataFrame: DataFrame containing the 1 minute data.
        """
        current_start = end_date - timedelta(days=7)
        current_end = end_date
        while current_start > start_date:
            super().get_ohlcv_1min(
                symbol=symbol,
                start_date=current_start,
                end_date=current_end,
            )
            current_end = current_start
            current_start -= timedelta(days=7)

        if current_start < start_date:
            super().get_ohlcv_1min(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
            )

        return super().get_ohlcv_1min(symbol, start_date, end_date)

    def get_maximum_1min_data(
        self, symbol: str, exchange: str = "NYSE"
    ) -> pd.DataFrame:
        """
        Gets the maximum 1 minute data for the given symbol.
        Args:
            symbol (str): The stock ticker symbol.
            exchange (str): The market exchange identifier (default is "NYSE").
        Returns:
            pd.DataFrame: The maximum 1 minute data for the symbol.
        """
        today = date.today()
        is_open = is_market_open_today(exchange)
        end_date = today + timedelta(days=1) if is_open else today

        if self._is_local_1min_data_beyond_30_days(symbol):
            # remove the local data if it is beyond 30 days
            os.remove(self._get_local_data_path(symbol, TimeGranularity.ONE_MINUTE))

            start_date = end_date - timedelta(days=30)
        else:
            local_start_date = self._get_1min_data_range(symbol)[0]
            start_date = (
                local_start_date
                if local_start_date < end_date - timedelta(days=30)
                else end_date - timedelta(days=30)
            )

        return self.get_ohlcv_1min(symbol, start_date, end_date)

    def get_30d_1min_data(self, symbol: str, exchange: str = "NYSE") -> pd.DataFrame:
        """
        Gets the 30 days of 1 minute data for the given symbol.

        Args:
            symbol (str): The stock ticker symbol.
            exchange (str): The market exchange identifier (default is "NYSE").

        Returns:
            pd.DataFrame: DataFrame containing the 30 days of 1 minute data.
        """
        today = date.today()
        is_open = is_market_open_today(exchange)
        end_date = today + timedelta(days=1) if is_open else today
        start_date = end_date - timedelta(days=30)
        return self.get_ohlcv_1min(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
        )
