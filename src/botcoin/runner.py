import uuid
from asyncio import Queue


from botcoin.utils.log import logging
from botcoin.data.dataclasses import Event, TickEvent, MarketOrder, PlaceOrderEvent, OrderStatusEvent


class StrategyRunner:
    '''
    This class is responsible for running the strategy.
    '''
    
    logger = logging.getLogger(__qualname__)
    
    def __init__(self, runner_queue: Queue, broker_queue: Queue):
        self.runner_queue = runner_queue
        self.broker_queue = broker_queue
        self.orders = []
   
   
    async def run(self):
        """
        This method starts the strategy runner.
        """
        while True:
            event = await self.runner_queue.get()
            await self.on_Event(event)
            self.runner_queue.task_done()
            if len(self.orders) > 0:
                await self.place_order()
   
    async def on_Event(self, evt: Event):
        """
        This method is called when an event occurs.
        :param event: The event that occurred.
        """
        self.logger.debug(f"Received event: {evt}")
        
        if isinstance(evt, TickEvent):
            if self.decide(evt):
                order = MarketOrder(
                    order_id=str(uuid.uuid4()),
                    symbol=evt.symbol,
                    quantity=1,  # Example quantity
                    direction="buy",  # Example direction
                )
                self.orders.append(order)
                
        elif isinstance(evt, OrderStatusEvent):
            order_id = evt.order.order_id
            self.logger.info(f'Received order status: {evt.status} for order ID: {order_id}')
            
                    
    async def place_order(self):
        """
        This method places an order.
        """
        for order in self.orders:
            evt = PlaceOrderEvent(order=order, reply_to=self.runner_queue)
            await self.broker_queue.put(evt)
            self.logger.info(f"Order placed: {order.order_id}")

        self.orders.clear()
        
    def decide(self, evt: TickEvent):

        """
        This method decides whether to trade or not.
        :param event: The event that occurred.
        :return: 
        """
        
        return True
    