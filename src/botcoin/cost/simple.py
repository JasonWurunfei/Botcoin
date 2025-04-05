class SimpleTradeCost:
    """
    A simple trade cost model that charges a fixed percentage of the trade amount.
    """

    def __init__(self, cost_percentage: float):
        """
        Initialize the SimpleTradeCost model.

        :param cost_percentage: The percentage of the trade amount to charge as cost.
        """
        self.cost_percentage = cost_percentage

    def calculate_cost(self, trade_amount: float) -> float:
        """
        Calculate the trade cost based on the trade amount.

        :param trade_amount: The amount of the trade.
        :return: The calculated trade cost.
        """
        return trade_amount * self.cost_percentage