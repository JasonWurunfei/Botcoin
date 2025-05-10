"""This module provides a async client for the Finnhub API."""

import os
import json
import aiohttp

import finnhub
from dotenv import load_dotenv

load_dotenv()
FINNHUB_API_KEY = os.getenv("FINNHUB_TOKEN")


class FinnhubClient:
    """
    This class provides a async client for the Finnhub API.
    """

    def __init__(self, api_key: str = None, timeout: int = 10):
        self.api_key = api_key or FINNHUB_API_KEY
        self.base_url = "https://api.finnhub.io/api/v1"
        self.default_headers = {
            "Accept": "application/json",
            "User-Agent": "finnhub/python",
            "X-Finnhub-Token": FINNHUB_API_KEY,
        }
        self.timeout = timeout

    async def _request(self, method, path, **kwargs) -> dict:
        """
        This method makes a request to the Finnhub API.

        :param method: The HTTP method to use (GET, POST, etc.).
        :param path: The path of the API endpoint.
        :param kwargs: Additional arguments to pass to the request.
        :return: The response from the API.
        """
        url = f"{self.base_url}{path}"
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        async with aiohttp.ClientSession(headers=self.default_headers, timeout=timeout) as session:
            kwargs["params"] = self._format_params(kwargs.get("params", {}))
            async with session.request(method, url, **kwargs) as response:
                return await response.json()

    async def _get(self, path: str, **kwargs) -> dict:
        """
        This method makes a GET request to the Finnhub API.

        :param path: The path of the API endpoint.
        :param kwargs: Additional arguments to pass to the request.
        :return: The response from the API.
        """
        return await self._request("GET", path, **kwargs)

    @staticmethod
    def _format_params(params):
        """
        This method formats the parameters for the request.
        It converts boolean values to JSON strings and replaces None with empty strings.
        :param params: The parameters to format.
        :return: The formatted parameters.
        """
        for key, value in params.items():
            if isinstance(value, bool):
                params[key] = json.dumps(value)
            if value is None:
                params[key] = ""
        return params

    async def quote(self, symbol: str) -> dict:
        """
        This method retrieves the quote for a given symbol.

        :param symbol: The symbol to retrieve the quote for.
        :return: The quote for the given symbol.

        Documentation: https://finnhub.io/docs/api/quote
        """
        path = "/quote"
        params = {"symbol": symbol}
        return await self._get(path, params=params)

    def quote_sync(self, symbol: str) -> dict:
        """
        This method retrieves the quote for a given symbol synchronously.

        :param symbol: The symbol to retrieve the quote for.
        :return: The quote for the given symbol.
        """
        return finnhub.Client(api_key=self.api_key).quote(symbol)

    async def company_news(self, symbol: str, _from: str, to: str) -> dict:
        """
        This method retrieves the company news for a given symbol.
        :param symbol: The symbol to retrieve the news for.
        :param _from: The start date for the news.
            format: YYYY-MM-DD
        :param to: The end date for the news.
            format: YYYY-MM-DD
        :return: The company news for the given symbol.

        Documentation: https://finnhub.io/docs/api/company-news
        """
        return await self._get("/company-news", params={"symbol": symbol, "from": _from, "to": to})

    def company_news_sync(self, symbol: str, _from: str, to: str) -> dict:
        """
        This method retrieves the company news for a given symbol synchronously.
        :param symbol: The symbol to retrieve the news for.
        :param _from: The start date for the news.
            format: YYYY-MM-DD
        :param to: The end date for the news.
            format: YYYY-MM-DD
        :return: The company news for the given symbol.
        """
        return finnhub.Client(api_key=self.api_key).company_news(symbol, _from, to)

    async def company_basic_financials(self, symbol: str, metric: str = "all") -> dict:
        """
        This method retrieves the company basic financials for a given symbol.
        :param symbol: The symbol to retrieve the financials for.
        :param metric: The metric to retrieve.
            Possible values: "all", "margin", "growth", "ratios"
        :return: The company basic financials for the given symbol.

        Documentation: https://finnhub.io/docs/api/company-basic-financials
        """
        return await self._get("/stock/metric", params={"symbol": symbol, "metric": metric})

    def company_basic_financials_sync(self, symbol: str, metric: str = "all") -> dict:
        """
        This method retrieves the company basic financials for a given symbol synchronously.
        :param symbol: The symbol to retrieve the financials for.
        :param metric: The metric to retrieve.
            Possible values: "all", "margin", "growth", "ratios"
        :return: The company basic financials for the given symbol.
        """
        return finnhub.Client(api_key=self.api_key).company_basic_financials(symbol, metric)

    async def stock_insider_transactions(self, symbol, _from=None, to=None):
        """
        This method retrieves the insider transactions for a given symbol.
        :param symbol: The symbol to retrieve the insider transactions for.
        :param _from: The start date for the transactions.
            format: YYYY-MM-DD
        :param to: The end date for the transactions.
            format: YYYY-MM-DD
        :return: The insider transactions for the given symbol.

        Documentation: https://finnhub.io/docs/api/insider-transactions
        """
        return await self._get(
            "/stock/insider-transactions", params={"symbol": symbol, "from": _from, "to": to}
        )

    def stock_insider_transactions_sync(self, symbol, _from=None, to=None):
        """
        This method retrieves the insider transactions for a given symbol synchronously.
        :param symbol: The symbol to retrieve the insider transactions for.
        :param _from: The start date for the transactions.
            format: YYYY-MM-DD
        :param to: The end date for the transactions.
            format: YYYY-MM-DD

        :return: The insider transactions for the given symbol.
        """
        return finnhub.Client(api_key=self.api_key).stock_insider_transactions(symbol, _from, to)
