"""This module contains the StepperService class."""

import time
import asyncio
from datetime import datetime

from botcoin.services import Service
from botcoin.utils.log import logging
from botcoin.data.dataclasses.events import TimeStepEvent
from botcoin.utils.rabbitmq.async_client import AsyncAMQPClient


class Stepper(Service):
    """This class is used for synchronizing the time in a simulated trading environment."""

    logger = logging.getLogger(__qualname__)

    def __init__(self, from_: datetime, to: datetime, speed: float = 1, freq: float = 100) -> None:
        """
        Initializes the Stepper with the start and end time for the simulation.
        :param from_: The start time for the simulation.
        :param to: The end time for the simulation.
        :param speed: The speed of the simulation. Default is 1 (real-time).
        :param freq: The frequency of the TimeStep Event emission. Default is 100Hz.
        It should not exceed 200Hz as that may risk cumulating emit tasks causing memory issues.
        """
        self.from_: float = from_.timestamp()
        self.to: float = to.timestamp()
        self.speed: float = speed
        self.freq: float = freq
        self._time_step: float = 1 / self.freq

        self._async_client = AsyncAMQPClient()
        self._async_client.set_logger_name(self.__class__.__name__)

        self._start_time = None
        self.sim_time: float = self.from_

    def estimate_real_time(self) -> float:
        """
        Estimates the real time taken for the simulation.
        :return: The estimated real time in seconds.
        """
        return (self.to - self.from_) / self.speed

    async def start(self) -> None:
        """
        Starts the service.
        """
        try:
            self.logger.info("%s started.", self.__class__.__name__)
            self.logger.info(
                "Simulation time: from %s to %s",
                datetime.fromtimestamp(self.from_),
                datetime.fromtimestamp(self.to),
            )
            self.logger.info("Estimated real time: %s seconds", self.estimate_real_time())
            await self._async_client.connect()

            self._start_time = time.perf_counter()
            iteration = 0

            while True:
                # This iteration should finish executing before the target time
                target_time = self._start_time + iteration * self._time_step

                # Check if the simulation time has reached the end time
                if self.sim_time >= self.to:
                    self.logger.info("Simulation time reached the end time.")
                    break

                # Emit the TimeStep Event
                self.emit_time_step_event(time.perf_counter())

                # check if the current time is exceeding the target time
                now = time.perf_counter()
                if now < target_time:
                    # We are ahead of the target time, so we need to sleep
                    sleep_duration = target_time - now
                    if sleep_duration > 0:
                        await asyncio.sleep(sleep_duration)

                iteration += 1

        finally:
            await self.stop()

    async def stop(self) -> None:
        """
        Stops the service.
        """
        await self._async_client.close()
        self.logger.info("%s stopped.", self.__class__.__name__)

    def emit_time_step_event(self, curr_time: float) -> None:
        """
        Emits the TimeStep Event.
        :param curr_time: The current time in the simulation.
        """
        elapsed_sim_time = (curr_time - self._start_time) * self.speed
        self.sim_time = self.from_ + elapsed_sim_time
        event = TimeStepEvent(timestamp=self.sim_time)
        self._async_client.emit_event(event, quite=True)
