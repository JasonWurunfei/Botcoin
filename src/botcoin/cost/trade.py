"""This module is used to implement a simple trade cost model for the botcoin framework."""

import math


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


class CommissionTradeCost:
    """
    A commission-based trade cost model that charges a fixed amount per trade.
    """

    def __init__(self, fee_rate: 0.0008, minimum_fee: 1):
        """
        Initialize the CommissionTradeCost model.

        Args:
            fee_rate (float): The commission fee rate as a percentage.
            minimum_fee (float): The minimum fee to be charged per trade.
        """
        self.fee_rate = fee_rate
        self.minimum_fee = minimum_fee

    def calculate_cost(self, trade_amount: float) -> float:
        """
        Calculate the trade cost based on the trade amount. The cost will
        be rounded ceil to 2 decimal places.

        Args:
            trade_amount (float): The amount of the trade.

        Returns:
            float: The calculated trade cost.
        """

        cost = trade_amount * self.fee_rate
        cost = math.ceil(cost * 100) / 100.0
        return max(cost, self.minimum_fee)
