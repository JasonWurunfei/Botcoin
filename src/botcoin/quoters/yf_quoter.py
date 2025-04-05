import yfinance as yf


class YFQuoter:
    """
    A class to get the price using Yahoo Finance.
    Documentation:
    https://yfinance-python.org/
    """
    @classmethod
    def get_lates_price(cls, ticker: str) -> float:
        price = yf.Ticker(ticker).history(period="1d")["Close"].iloc[-1]
        return price
    
    @classmethod
    def get_five_year_daily_prices(cls, ticker: str) -> list:
        """
        Get the last 5 years of daily prices for a given ticker.
        """
        # Define the ticker (e.g., BTC-USD, ETH-USD, AAPL, etc.)
        ticker = yf.Ticker(ticker)

        # Fetch 5 years of daily candles
        candles = ticker.history(period="5y", interval="1d")

        ohlc = candles[["Open", "High", "Low", "Close"]]

        return ohlc


if __name__ == "__main__":
    # Example usage
    print(YFQuoter.get_lates_price("mstr"))
    print(YFQuoter.get_five_year_daily_prices("mstr"))