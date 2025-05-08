# Botcoin
Botcoin is a develop tool kit for developing and automaticaly deploy trading strategy.

The problem with many tools for trading is that it often back test their results on charts and always assumes they will get the market price. However, this is hardly anywhere close to real life trading. For retail traders, there is normally a huge delay when they receive the new price tick and the actual market price (at least with many free APIs, they are often 15 minutes delay), not to mention the delay between their trading app and their brokerages. Furthermore, the bid/ask spread is often huge, and the market price is not always available. This means that even if you have a good strategy, it may not work in real life. 

Botcoin provides a powerful infrastructure to quickly validate trading strategy that simulates real world trading environment. There are mainly five components in Botcoin:
1. **Data provider**: This is the data source for the trading strategy. It can be a real time data source or a historical data source. The data provider is responsible for providing the data to the trading strategy. It can be configured to support different data sources, such as Finnhub, Alpaca, Binance, etc. The data provider is also responsible for providing the data in a format that is compatible with the trading strategy.
2. **Trade Runner**: This component executes the trading strategy based on the data provided. It handles order placement and performance tracking.
3. **Strategy**: This is the core of the trading system. It contains the logic for making trading decisions based on the data provided by the data provider. The strategy can be implemented using different algorithms, such as moving average, RSI, etc.
4. **Risk management**: This component is responsible for managing the risk associated with the trading strategy. It can be configured to support different risk management techniques, such as stop loss, take profit, etc.
5. **Brokerage**: This component is responsible for executing the trades on the brokerage platform. Botcoin implemented a simulated brokerage that simulates the real world trading environment. It can be configured to support different brokerage platforms, such as Saxo, Binance, etc.


## Strategy development
The notebooks folder contains all the notebooks for developing the trading strategy. It explains how to use the data provider, trading engine, strategy, risk management, and brokerage components. It also provides examples of how to implement different trading strategies using the Botcoin framework and discover new ideas.

## To Run tests
Run the following comand to install the required packages.

```bash
pip install -r requirements.txt
```

You need to set the `PYTHONPATH` to `src` such that vscode knows where to look for the source code. So just create a `.env` file and add

```.env
PYTHONPATH=src
```

To make sure the Finnhub Historical data manager works, you need to put your API key in `.env` file as well.

```.env
FINNHUB_TOKEN=you-api-key
```

If you use VSCode, you should also set the following variables in the settings.json file.

```json
{
    "python.envFile": "${workspaceFolder}/.env",
    "python.analysis.extraPaths": [
        "./src",
        "./tests"
    ],
    "python.analysis.typeCheckingMode": "basic"
}
```

## Run Botcoin API
### Environment variables
You need to set the following environment variables in `.env` file.

```.env
LOG_LEVEL=INFO
PYTHONPATH=./src

## FastAPI
FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=8000
WORKERS=1

# RabbitMQ
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest
RABBITMQ_EXCHANGE=botcoin

# Account Service
SERVICE_QUEUE=account_service

# API Keys
FINNHUB_TOKEN=your-api-key

# Email
NOTIFY_EMAIL_ADDRESS=your-email-address@example.com
NOTIFY_EMAIL_PASSWORD=your-email-password
```

Remember to put in your Finnhub API key and email credentials. Then you can use docekr compose to run the Botcoin API.

```bash
docker-compose up -d
```

## Available features
- [x] Real-time price ticker `botcoin.data.tickers.FinnhubTicker`.
- [x] Historical data manager `botcoin.data.historical.YfDataManager`.
    - [x] Manage downloading historical data from Yahoo Finance.
    - [x] Manage local historical data storage.
    - [x] Manage historical data retrieval from local storage.
- [x] Simulated brokerage `botcoin.brokerage.SimpleBroker`.
    - [x] Simulated order placement.
    - [x] Simulated order execution.
        - [x] Simulated market order.
        - [x] Simulated limit order.
        - [ ] Simulated stop order.
    - [x] Simulated order cancellation.
- [x] Simulated price steam data from OHLC data frame `botcoin.utils.stream_data.generate_price_stream`.
- [x] FastAPI Interface
    - [x] utility functions to compute OCO orders.
    - [ ] interface strategy with FastAPI.
    - [ ] interface brokerage with FastAPI.
- [x] Plotly for visualizing the trading strategy.
