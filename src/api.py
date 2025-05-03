"""This script is used to interact with botcoin runner"""

import os
from datetime import datetime

import uvicorn
from fastapi import FastAPI
from dotenv import load_dotenv

from botcoin.cost.trade import CommissionTradeCost
from botcoin.data.dataclasses.events import StartEvent, StopEvent, RequestTickEvent
from botcoin.utils.rabbitmq.event import emit_event


load_dotenv()


DESC = """
Botcoint. 🚀

Welcome to the Botcoin API documentation!

"""

app = FastAPI(
    title="Botcoin",
    description=DESC,
    summary="Botcoin API",
    version="0.0.1",
    license_info={
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
    },
)

commission_trade_cost = CommissionTradeCost(fee_rate=0.0008, minimum_fee=1)


@app.get("/risk")
def risk_sell(
    risk_amount: float, num_of_shares: int, open_price: float, loss_win_ratio: float
) -> dict:
    """
    Compute risk sell OCO order. It will return a dictionary with the following keys:
    - `limit_price`: The limit price for the sell order.
    - `stop_price`: The stop price for the sell order.
    - `risk_per_share`: The risk amount per share.
    - `risk_percent`: The risk percentage.
    - `gain_per_share`: The gain amount per share.
    - `gain_percent`: The gain percentage.
    - `commission`: The commission cost for the trade.


    Args:
    - `risk_amount` (float): The amount of risk you are willing to take.
    - `num_of_shares` (int): The number of shares you are selling.
    - `open_price` (float): The price at which you opened the position.
    - `loss_win_ratio` (float): The ratio of loss to win.

    Returns:
        dict: A dictionary containing the limit price, stop price, risk per share, gain per share,
        and their respective percentages, along with the commission cost.
    """
    risk_per_share = risk_amount / num_of_shares
    gain_per_share = risk_per_share / loss_win_ratio
    limit_price = open_price + gain_per_share
    stop_price = open_price - risk_per_share
    risk_percent = (risk_per_share / open_price) * 100
    gain_percent = (gain_per_share / open_price) * 100
    return {
        "limit_price": round(limit_price, 2),
        "stop_price": round(stop_price, 2),
        "risk_per_share": round(risk_per_share, 2),
        "risk_percent": round(risk_percent, 2),
        "gain_per_share": round(gain_per_share, 2),
        "gain_percent": round(gain_percent, 2),
        "commission_fee": commission_trade_cost.calculate_cost(
            num_of_shares * open_price
        ),
    }


@app.get("/ticker/start")
async def start_ticker(symbol: str) -> dict:
    """
    Start the ticker for a given symbol.

    Args:
        symbol (str): The symbol to start the ticker for.

    Returns:
        dict: A message indicating that the ticker has started.
    """
    await emit_event(RequestTickEvent(symbol=symbol))

    return {
        "message": f"Ticker started for {symbol}",
    }


@app.get("/practice/historical/start")
async def start_practice() -> dict:
    # async def start_practice(start_date: str, end_date: str) -> dict:
    """
    Start the practice session.

    Args:
        start_date (str): The start date for the practice session.
            format: YYYY-MM-DD HH:MM:SS
        end_date (str): The end date for the practice session.
            format: YYYY-MM-DD HH:MM:SS

    Returns:
        dict: A message indicating that the practice session has started.
    """

    await emit_event(StartEvent())

    return {
        "message": "Practice session started",
    }


@app.get("/practice/historical/stop")
async def stop_practice() -> dict:
    """
    Stop the practice session.

    Returns:
        dict: A message indicating that the practice session has stopped.
    """

    await emit_event(StopEvent())

    return {
        "message": "Practice session stopped",
    }


if __name__ == "__main__":
    try:
        host = os.getenv("FastAPI_HOST", "0.0.0.0")
        port = int(os.getenv("FastAPI_PORT", "8000"))
        workers = int(os.getenv("FastAPI_WORKERS", "1"))
        uvicorn.run(app, host=host, port=port, workers=workers)
    except KeyboardInterrupt:
        print("Server stopped by user.")
    finally:
        print("Cleaning up...")
