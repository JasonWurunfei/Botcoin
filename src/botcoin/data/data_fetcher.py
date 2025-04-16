import os
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import pytz


class HistoricalDataManager:
    """
    A class to manage and fetch 1-minute candlestick data from Yahoo Finance.
    Data is stored locally to avoid repeated requests for the same data.

    Attributes:
        ticker (str): The stock ticker symbol.
        data_folder (str): Folder where data will be saved locally.
        tz (str): Timezone for the data, default is 'US/Eastern'.
    """

    def __init__(self, ticker: str, data_folder: str = 'data', tz: str = 'US/Eastern'):
        """
        Initializes the HistoricalDataManager with the given ticker and data folder.

        Args:
            ticker (str): The stock ticker symbol to fetch data for.
            data_folder (str, optional): Folder to store local data. Defaults to 'data'.
        """
        self.ticker = ticker
        self.data_folder = data_folder
        self.tz = pytz.timezone(tz)
        if not os.path.exists(self.data_folder):
            os.makedirs(self.data_folder)
        self.data = self._load_local_data()
        

    def _get_local_data_path(self) -> str:
        """
        Returns the local file path where the data for the ticker is stored.

        Returns:
            str: Local path to the data file.
        """
        return os.path.join(self.data_folder, f"{self.ticker}_1min_data.parquet")

    def _fetch_data(self, start: datetime, end: datetime) -> pd.DataFrame:
        """
        Fetches 1-minute interval candlestick data from Yahoo Finance, split into chunks if necessary.

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
            print(f"Fetching data from {current_start} to {current_end}")

            # Fetch data from yfinance
            df = yf.download(
                self.ticker,
                start=current_start,
                end=current_end,
                interval="1m",
                progress=False,
                multi_level_index=False,
            )

            if not df.empty:
                df.index = pd.to_datetime(df.index)
                df.index = df.index.tz_convert(self.tz)
                df = df[~df.index.duplicated(keep='last')]  # Remove duplicated index
                all_data.append(df)

            current_start = current_end

        return pd.concat(all_data) if all_data else pd.DataFrame()        

    def _check_data_in_local(self, start: datetime, end: datetime) -> bool:
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
            local_start =  local_data.index.min()
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
            self.data = self.data[~self.data.index.duplicated(keep='last')].sort_index()
            # Save the merged data back to local storage
            self.data.to_parquet(self._get_local_data_path())
            print(f"Data merged and saved to {self._get_local_data_path()}")
        else:
            print("No new data to merge.")
        

    def get_data(self, start: datetime, end: datetime) -> pd.DataFrame:
        """
        Retrieves 1-minute candlestick data for the specified date range. 
        If data is available locally, it will be used. If not, it will be fetched from Yahoo Finance.

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
        if self._check_data_in_local(start, end):
            print("Loading data from local storage...")
            return self.data[(self.data.index >= start) & (self.data.index <= end)]

        # Fetch data from Yahoo Finance if not available locally
        print("Fetching new data...")
        df = self._fetch_data(start, end)

        # Save the fetched data locally for future use
        if not df.empty:
            self._merge_data(df)
        
        return df

import os
import json
import websocket
from dotenv import load_dotenv

# Load variables from .env file into environment
load_dotenv()


class PriceTicker:
    """
    A class to manage and fetch real-time price data for a list of stock tickers.
    """

    def __init__(self, tickers:  list[str], tz: str = 'US/Eastern'):
        """
        Initializes the PriceTicker with the given list of tickers.

        Args:
            ticker (list[str]): List of stock ticker symbols.
            tz (str, optional): Timezone for the data, default is 'US/Eastern'.
        """
        self.tickers = tickers
        self.tz = pytz.timezone(tz)
        
        def on_open(ws):
            for ticker in self.tickers:
                ws.send(json.dumps({"type": "subscribe", "symbol": ticker}))
                
        def on_message(ws, message):
            msg = json.loads(message)
            # print(json.dumps(data, indent=4))
            records = msg.get("data", None)
            if records:
                for record in records:
                    t = datetime.fromtimestamp(record["t"] / 1000, tz=self.tz)
                    p = float(record["p"])
                    s = record["s"]
                    self.on_message(s, t, p)

        def on_error(ws, error):
            print(error)

        def on_close(ws):
            print("### closed ###")
                
        self.ws = websocket.WebSocketApp(
            f"wss://ws.finnhub.io?token={os.getenv('FINNHUB_TOKEN')}",
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
        )
        self.ws.on_open = on_open
        
    
    def tick(self):
        """
        Starts the WebSocket connection to fetch real-time price data.
        """
        self.ws.run_forever()
        

    def on_message(self, s, t, p):
        """
        Callback function to handle incoming messages.
        
        Args:
            s (str): The stock ticker symbol.
            t (datetime): The timestamp of the price update.
            p (float): The price of the stock.
        """
        # Process the message as needed
        print(f"{t} - {s}: {p}")

            