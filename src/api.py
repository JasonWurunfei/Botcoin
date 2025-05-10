"""This script is used to interact with botcoin runner"""

import os

import uvicorn
from fastapi import FastAPI
from dotenv import load_dotenv

from botcoin.cost.trade import CommissionTradeCost
from botcoin.data.dataclasses.events import (
    StartEvent,
    StopEvent,
    RequestTickEvent,
    RequestStopTickEvent,
    PlaceOrderEvent,
)
from botcoin.data.dataclasses.order import MarketOrder
from botcoin.utils.rabbitmq.async_client import AsyncAMQPClient


load_dotenv()
account_service_queue = os.getenv("SERVICE_QUEUE", "account_service")

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
async_client = AsyncAMQPClient()


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
        "commission_fee": commission_trade_cost.calculate_cost(num_of_shares * open_price),
    }


@app.get("/account/balance")
async def get_account_balance() -> dict:
    """
    Get the account balance.

    Returns:
        dict: A message indicating that the command has been sent.
    """
    return await async_client.call(
        url="/account/balance",
        server_qname=account_service_queue,
    )


@app.get("/account/stocks")
async def get_account_stocks() -> dict:
    """
    Get the account stocks.

    Returns:
        dict: A message indicating that the command has been sent.
    """
    return await async_client.call(
        url="/account/stocks",
        server_qname=account_service_queue,
    )


@app.get("/account/value")
async def get_account_value() -> dict:
    """
    Get the account value.

    Returns:
        dict: A message indicating that the command has been sent.
    """
    return await async_client.call(
        url="/account/value",
        server_qname=account_service_queue,
    )


@app.get("/account/increase_cash")
async def increase_cash(amount: float) -> dict:
    """
    Increase the account cash.

    Args:
        amount (float): The amount to increase.

    Returns:
        dict: A message indicating that the command has been sent.
    """
    return await async_client.call(
        url=f"/increase_cash?amount={amount}", server_qname=account_service_queue
    )


@app.get("/account/decrease_cash")
async def decrease_cash(amount: float) -> dict:
    """
    Decrease the account cash.

    Args:
        amount (float): The amount to decrease.

    Returns:
        dict: A message indicating that the command has been sent.
    """
    return await async_client.call(
        url=f"/decrease_cash?amount={amount}", server_qname=account_service_queue
    )


@app.get("/account/buy_stock")
async def buy_stock(symbol: str, quantity: int, price: float) -> dict:
    """
    Buy a stock.

    Args:
        symbol (str): The stock symbol.
        quantity (int): The quantity to buy.
        price (float): The price to buy at.

    Returns:
        dict: A message indicating that the command has been sent.
    """
    symbol = symbol.upper()
    if quantity <= 0:
        return {"error": "Quantity must be greater than zero."}
    if price <= 0:
        return {"error": "Price must be greater than zero."}

    return await async_client.call(
        url=f"/buy_stock?symbol={symbol}&quantity={quantity}&price={price}",
        server_qname=account_service_queue,
    )


@app.get("/account/sell_stock")
async def sell_stock(symbol: str, quantity: int, price: float) -> dict:
    """
    Sell a stock.

    Args:
        symbol (str): The stock symbol.
        quantity (int): The quantity to sell.
        price (float): The price to sell at.

    Returns:
        dict: A message indicating that the command has been sent.
    """
    symbol = symbol.upper()
    if quantity <= 0:
        return {"error": "Quantity must be greater than zero."}
    if price <= 0:
        return {"error": "Price must be greater than zero."}

    return await async_client.call(
        url=f"/sell_stock?symbol={symbol}&quantity={quantity}&price={price}",
        server_qname=account_service_queue,
    )


@app.get("/ticker/start")
async def start_ticker(symbol: str) -> dict:
    """
    Start the ticker for a given symbol.

    Args:
        symbol (str): The symbol to start the ticker for.

    Returns:
        dict: A message indicating that the command has been sent.
    """
    symbol = symbol.upper()
    async_client.emit_event(RequestTickEvent(symbol=symbol))

    return {
        "message": f"Tick command sent for {symbol}",
    }


@app.get("/ticker/stop")
async def stop_ticker(symbol: str) -> dict:
    """
    Stop the ticker for a given symbol.

    Args:
        symbol (str): The symbol to stop the ticker for.

    Returns:
        dict: A message indicating that the command has been sent.
    """
    symbol = symbol.upper()
    async_client.emit_event(RequestStopTickEvent(symbol=symbol))

    return {
        "message": f"Stop tick command sent for {symbol}",
    }


@app.get("/order/place/market")
async def place_market_order(symbol: str, quantity: int, direction: str) -> dict:
    """
    Place a market order.

    Args:
        symbol (str): The symbol for the order.
        quantity (int): The quantity of the order.
        direction (str): The direction of the order ("buy" or "sell").

    Returns:
        dict: A message indicating that the order has been placed.
    """
    symbol = symbol.upper()

    if direction not in ["buy", "sell"]:
        return {"error": "Invalid direction. Use 'buy' or 'sell'."}

    if quantity <= 0:
        return {"error": "Quantity must be greater than zero."}

    order = MarketOrder(
        symbol=symbol,
        quantity=quantity,
        direction=direction,
    )

    async_client.emit_event(PlaceOrderEvent(order=order))

    return {
        "message": f"Market order placed for {symbol} "
        + f"with quantity {quantity} and direction {direction}",
    }


@app.get("/start")
async def start_botcoin() -> dict:
    """
    Start Botcoin.
    """

    async_client.emit_event(StartEvent())

    return {
        "message": "Botcoin start command sent",
    }


@app.get("/stop")
async def stop_botcoin() -> dict:
    """
    Stop Botcoin.
    """

    async_client.emit_event(StopEvent())

    return {
        "message": "Botcoin stop command sent",
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
