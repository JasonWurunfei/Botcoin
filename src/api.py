"""This script is used to interact with botcoin runner"""

# import uuid
import os
import json
from dataclasses import asdict

# from dataclasses import asdict

import uvicorn
import aio_pika
from fastapi import FastAPI
from dotenv import load_dotenv

from botcoin.cost.trade import CommissionTradeCost
from botcoin.data.dataclasses import StartEvent, StopEvent


load_dotenv()
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASSWORD", "guest")
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_EXCHANGE = os.getenv("RABBITMQ_EXCHANGE", "botcoin")
RABBITMQ_URL: str = (
    f"amqp://{RABBITMQ_USER}:{RABBITMQ_PASS}@{RABBITMQ_HOST}:{RABBITMQ_PORT}"
)

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

    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    async with connection:
        channel = await connection.channel()  # Creating a channel
        exchange = await channel.get_exchange(RABBITMQ_EXCHANGE)

        body = StartEvent().to_json()

        message = aio_pika.Message(
            body=json.dumps(body).encode(),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,  # Ensures the message is saved in case of RabbitMQ restart
        )

        await exchange.publish(message, routing_key="")

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

    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    async with connection:
        channel = await connection.channel()  # Creating a channel
        exchange = await channel.get_exchange(RABBITMQ_EXCHANGE)

        body = StopEvent().to_json()

        message = aio_pika.Message(
            body=json.dumps(body).encode(),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,  # Ensures the message is saved in case of RabbitMQ restart
        )

        await exchange.publish(message, routing_key="")

    return {
        "message": "Practice session stopped",
    }


# @app.get("/practice/historical/order/market")
# async def place_order(
#     symbol: str,
#     direction: str,
#     quantity: int,
# ) -> dict:
#     """
#     Place a market order.

#     Args:
#         symbol (str): The stock symbol.
#         direction (str): The direction of the order (buy/sell).
#         quantity (int): The quantity of shares.

#     Returns:
#         dict: A message indicating that the order has been placed.
#     """

#     order = MarketOrder(
#         order_id=str(uuid.uuid4()),
#         symbol=symbol,
#         quantity=quantity,
#         direction=direction,
#     )
#     order_event = PlaceOrderEvent(order=order, reply_to=server_queue)
#     print("1")
#     await broker_queue.put(order_event)
#     print("2")
#     order_status_event = await server_queue.get()
#     print("3")
#     orderbook[order.order_id] = {
#         "order": asdict(order),
#         "status": order_status_event.status,
#     }
#     server_queue.task_done()
#     return asdict(order_status_event)


# @app.get("/practice/historical/order/limit")
# async def place_limit_order(
#     symbol: str,
#     direction: str,
#     quantity: int,
#     limit_price: float,
# ) -> dict:
#     """
#     Place a limit order.

#     Args:
#         symbol (str): The stock symbol.
#         direction (str): The direction of the order (buy/sell).
#         quantity (int): The quantity of shares.
#         limit_price (float): The limit price for the order.

#     Returns:
#         dict: A message indicating that the order has been placed.
#     """

#     order = LimitOrder(
#         order_id=str(uuid.uuid4()),
#         symbol=symbol,
#         quantity=quantity,
#         direction=direction,
#         limit_price=limit_price,
#     )
#     order_event = PlaceOrderEvent(order=order, reply_to=server_queue)
#     await broker_queue.put(order_event)
#     order_status_event = await server_queue.get()
#     orderbook[order.order_id] = {
#         "order": asdict(order),
#         "status": order_status_event.status,
#     }
#     server_queue.task_done()
#     return asdict(order_status_event)


if __name__ == "__main__":
    try:
        host = os.getenv("HOST", "0.0.0.0")
        port = int(os.getenv("PORT", "8000"))
        workers = int(os.getenv("WORKERS", "1"))
        uvicorn.run(app, host=host, port=port, workers=workers)
    except KeyboardInterrupt:
        print("Server stopped by user.")
    finally:
        print("Cleaning up...")
