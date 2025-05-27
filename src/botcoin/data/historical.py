"""This module is used to fetch historical and real-time data for stock symbols."""

from abc import ABC, abstractmethod
from enum import Enum
import os
from datetime import datetime, timedelta, date

import pytz
import pandas as pd
import yfinance as yf
from dotenv import load_dotenv

from botcoin.utils.log import logging


# Load variables from .env file into environment
load_dotenv()


class YfDataManager:
    """
    A class to manage and fetch 1-minute candlestick data from Yahoo Finance.
    Data is stored locally to avoid repeated requests for the same data.

    Attributes:
        symbol (str): The stock ticker symbol.
        data_folder (str): Folder where data will be saved locally.
        tz (str): Timezone for the data, default is 'US/Eastern'.
    """

    logger = logging.getLogger(__qualname__)

    def __init__(self, symbol: str, data_folder: str = "data", tz: str = "US/Eastern"):
        """
        Initializes the HistoricalDataManager with the given symbol and data folder.

        Args:
            symbol (str): The stock symbol symbol to fetch data for.
            data_folder (str, optional): Folder to store local data. Defaults to 'data'.
        """
        self.symbol = symbol
        self.data_folder = data_folder
        self.tz = pytz.timezone(tz)
        if not os.path.exists(self.data_folder):
            os.makedirs(self.data_folder)
        self.data = self._load_local_data()

    def _get_local_data_path(self) -> str:
        """
        Returns the local file path where the data for the symbol is stored.

        Returns:
            str: Local path to the data file.
        """
        return os.path.join(self.data_folder, f"{self.symbol}_1min_data.parquet")

    def _fetch_data(self, start: datetime, end: datetime) -> pd.DataFrame:
        """
        Fetches 1-minute interval candlestick data from Yahoo Finance,
        split into chunks if necessary.

        Args:
            start (datetime): Start date and time for the data request.
            end (datetime): End date and time for the data request.

        Returns:
            pd.DataFrame: DataFrame containing the 1-minute candlestick data.
        """
        max_days = 7  # Yahoo Finance limits to ~7 days for 1m interval
        all_data = []

        current_start = start
        while current_start < end:
            current_end = min(current_start + timedelta(days=max_days), end)
            self.logger.info("Fetching data from %s to %s", current_start, current_end)

            # Fetch data from yfinance
            df = yf.download(
                self.symbol,
                start=current_start,
                end=current_end,
                interval="1m",
                progress=False,
                multi_level_index=False,
            )

            if not df.empty:
                df.index = pd.to_datetime(df.index)
                df.index = df.index.tz_convert(self.tz)
                df = df[~df.index.duplicated(keep="last")]  # Remove duplicated index
                all_data.append(df)

            current_start = current_end

        return pd.concat(all_data) if all_data else pd.DataFrame()

    def check_data_in_local(self, start: datetime, end: datetime) -> bool:
        """
        Checks if data for the given date range already exists in local storage.

        Args:
            start (datetime): Start date and time for the data request.
            end (datetime): End date and time for the data request.

        Returns:
            bool: True if the data exists in local storage, False otherwise.
        """
        data_path = self._get_local_data_path()

        if os.path.exists(data_path):
            local_data = self.data
            local_start = local_data.index.min()
            local_end = local_data.index.max()

            # If the requested range is within the range of the local data, no need to fetch
            if local_start <= start and local_end >= end:
                return True
        return False

    def _load_local_data(self) -> pd.DataFrame:
        """
        Loads the data from local storage.

        Returns:
            pd.DataFrame: DataFrame containing the local data.
        """
        data_path = self._get_local_data_path()
        if os.path.exists(data_path):
            df = pd.read_parquet(data_path)
            df.index = pd.to_datetime(df.index)
            df.index = df.index.tz_convert(self.tz)
            return df
        return pd.DataFrame()

    def _merge_data(self, new_data: pd.DataFrame) -> None:
        """
        Merges new data into the existing local data.

        Args:
            new_data (pd.DataFrame): New data to be merged.
        """
        if not new_data.empty:
            # Concatenate new data with existing data
            self.data = pd.concat([self.data, new_data])
            # Drop duplicates and sort by index
            self.data = self.data[~self.data.index.duplicated(keep="last")].sort_index()
            # Save the merged data back to local storage
            self.data.to_parquet(self._get_local_data_path())
            self.logger.info("Data merged and saved to %s", self._get_local_data_path())
        else:
            self.logger.warning("No new data to merge.")

    def get_data(self, start: datetime, end: datetime) -> pd.DataFrame:
        """
        Retrieves 1-minute candlestick data for the specified date range.
        If data is available locally, it will be used. If not, it will be
        fetched from Yahoo Finance.

        Args:
            start (datetime): Start date and time for the data request.
            end (datetime): End date and time for the data request.

        Returns:
            pd.DataFrame: DataFrame containing the 1-minute candlestick data.
        """
        # Ensure the start is before the end
        if start > end:
            raise ValueError("Start date must be before end date.")

        # Ensure the date range is within the last 30 days
        today = datetime.today().replace(tzinfo=self.tz)
        if start < today - timedelta(days=30):
            raise ValueError("Data requests cannot go beyond 30 days in the past.")

        # Check if data is already available locally
        if self.check_data_in_local(start, end):
            self.logger.info("Data is already available locally.")
            return self.data[(self.data.index >= start) & (self.data.index <= end)]

        # Fetch data from Yahoo Finance if not available locally
        self.logger.info("Fetching data from Yahoo Finance.")
        df = self._fetch_data(start, end)

        # Save the fetched data locally for future use
        if not df.empty:
            self._merge_data(df)

        return df


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
        start: date,
        end: date,
        granularity: TimeGranularity,
    ) -> pd.DataFrame:
        """
        Fetches historical data for the specified date range.

        Args:
            symbol (str): The stock ticker symbol.
            start (date): Start date for the data request.
            end (date): End date for the data request.
            granularity (TimeGranularity): The time granularity for the data.

        Returns:
            pd.DataFrame: DataFrame containing the historical data.
            format: {datetime: [open, high, low, close, volume]}
        """

    def get_ohlcv_1min(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
    ) -> pd.DataFrame:
        """
        Fetches historical data for the specified date range with a default granularity of 1 minute.

        Args:
            symbol (str): The stock ticker symbol.
            start (datetime): Start date and time for the data request.
            end (datetime): End date and time for the data request.

        Returns:
            pd.DataFrame: DataFrame containing the historical data.
            format: {datetime: [open, high, low, close, volume]}
        """
        return self.get_ohlcv(symbol, start, end, TimeGranularity.ONE_MINUTE)


class YfDataProvider(DataProvider):
    """
    A concrete implementation of DataProvider that uses Yahoo Finance to fetch data.
    """

    def get_ohlcv(
        self,
        symbol: str,
        start: date,
        end: date,
        granularity: TimeGranularity,
    ) -> pd.DataFrame:
        # Fetch data from yfinance

        # Ensure the start is before the end
        if start > end:
            raise ValueError("Start date must be before end date.")

        # Set the start and end time to be before and after the market hours
        start = str(start)
        end = str(end)

        df = yf.download(
            tickers=symbol,
            start=start,
            end=end,
            interval=granularity.value,
            multi_level_index=False,
            progress=False,  # Disable progress bar
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

    def __init__(self, dp: DataProvider, data_folder: str = None, tz: str = "US/Eastern"):
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

        if start_date + timedelta(days=1) > end_date:
            raise ValueError("The date range must be at least 1 day.")

        df = self._get_local_data(symbol, TimeGranularity.ONE_MINUTE)
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
            new_df = self.dp.get_ohlcv_1min(symbol, start_date, end_date)
            self._save_local_data(new_df, symbol, TimeGranularity.ONE_MINUTE)
            return new_df

        local_start_date, local_end_date = self._get_date_range(df)

        # fetch new data and merge it with the local data
        self.logger.debug("Fetching new data and merging with local data.")
        if start_date + timedelta(days=1) < end_date:  # query for more than a single day
            if start_date >= local_end_date:
                # If the start date is after the last local data, fetch new data
                new_df = self.dp.get_ohlcv_1min(symbol, local_end_date, end_date)
                df = pd.concat([df, new_df])
                self._save_local_data(df, symbol, TimeGranularity.ONE_MINUTE)
                return df

            if end_date <= local_start_date:
                # If the end date is before the first local data, fetch new data
                new_df = self.dp.get_ohlcv_1min(symbol, start_date, local_start_date)
                df = pd.concat([new_df, df])
                self._save_local_data(df, symbol, TimeGranularity.ONE_MINUTE)
                return df

            if start_date < local_start_date <= end_date <= local_end_date:
                # If the start is before the local data and end is within the local data
                new_df = self.dp.get_ohlcv_1min(symbol, start_date, local_start_date)
                df = pd.concat([new_df, df])
                self._save_local_data(df, symbol, TimeGranularity.ONE_MINUTE)
                return df

            if local_start_date <= start_date < local_end_date < end_date:
                # If the start is after the local data and end is beyond the local data
                new_df = self.dp.get_ohlcv_1min(symbol, local_end_date, end_date)
                df = pd.concat([df, new_df])
                self._save_local_data(df, symbol, TimeGranularity.ONE_MINUTE)
                return df

            if start_date < local_start_date and end_date > local_end_date:
                # If the requested range is wider than the local data, fetch new data
                new_df_left = self.dp.get_ohlcv_1min(symbol, start_date, local_start_date)
                new_df_right = self.dp.get_ohlcv_1min(symbol, local_end_date, end_date)
                df = pd.concat([new_df_left, df, new_df_right])
                self._save_local_data(df, symbol, TimeGranularity.ONE_MINUTE)
                return df

        else:  # query for a single day
            if start_date < local_start_date:
                # If the start date is before the first local data, fetch new data
                new_df = self.dp.get_ohlcv_1min(symbol, start_date, local_start_date)
                df = pd.concat([new_df, df])
                self._save_local_data(df, symbol, TimeGranularity.ONE_MINUTE)
                return df

            if start_date >= local_end_date:
                # If the end date is after the last local data, fetch new data
                new_df = self.dp.get_ohlcv_1min(symbol, local_end_date, end_date)
                df = pd.concat([df, new_df])
                self._save_local_data(df, symbol, TimeGranularity.ONE_MINUTE)
                return df

    def _get_local_data(self, symbol: str, granularity: TimeGranularity) -> pd.DataFrame:
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
            df.index = pd.to_datetime(df.index)
            df.index = df.index.tz_convert(self.tz)
            return df
        return pd.DataFrame()

    def _save_local_data(self, df: pd.DataFrame, symbol: str, granularity: TimeGranularity) -> None:
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
        return os.path.join(self.data_folder, f"{symbol}_ohlcv_{granularity.value}.parquet")

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
