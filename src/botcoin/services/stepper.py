"""This module contains the StepperService class."""

import time
import asyncio
from datetime import datetime

import pytz

from botcoin.services import Service
from botcoin.utils.log import logging
from botcoin.utils.rabbitmq.event import EventReceiver
from botcoin.utils.rabbitmq.async_client import AsyncAMQPClient
from botcoin.data.dataclasses.events import (
    TimeStepEvent,
    SimStartEvent,
    SimStopEvent,
    Event,
)


class Stepper(Service, EventReceiver):
    """This class is used for synchronizing the time in a simulated trading environment."""

    logger = logging.getLogger(__qualname__)

    subscribedEvents = {
        SimStartEvent,
        SimStopEvent,
    }

    def __init__(
        self,
        from_: datetime,
        to: datetime,
        speed: float = 1,
        freq: float = 100,
        tz: str = "US/Eastern",
    ) -> None:
        """
        Initializes the Stepper with the start and end time for the simulation.
        :param from_: The start time for the simulation.
        :param to: The end time for the simulation.
        :param speed: The speed of the simulation. Default is 1 (real-time).
        :param freq: The frequency of the TimeStep Event emission. Default is 100Hz.
        It should not exceed 200Hz as that may risk cumulating emit tasks causing memory issues.
        :param tz: The timezone for the simulation. Default is US/Eastern.
        """
        self.from_: float = pytz.timezone(tz).localize(from_).timestamp()
        self.to: float = pytz.timezone(tz).localize(to).timestamp()
        self.tz = pytz.timezone(tz)
        self.speed: float = speed
        self.freq: float = freq
        self._time_step: float = 1 / self.freq

        self._async_client = AsyncAMQPClient()
        self._async_client.set_logger_name(self.__class__.__name__)
        self._adjust_freq = 100  # Adjust the padding time every 100 iterations

        # Simulation variables
        self.sim_time: float = self.from_
        self._start_time: float | None = None
        self._just_slept: bool = False
        self._before_sleep: float | None = None
        self._sleep_adjustment: float = 1
        self._planned_sleep_duration: float | None = None

        # Simulation Task
        self._simulation_task = None

    def _sim_init(self) -> None:
        """
        Initializes the simulation.
        """

        self.sim_time = self.from_
        self._start_time = None
        self._just_slept = False
        self._before_sleep = None
        self._sleep_adjustment = 1
        self._planned_sleep_duration = None

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
            await self._async_client.connect()

            await asyncio.Event().wait()  # block forever

        finally:
            await self.stop()

    async def stop(self) -> None:
        """
        Stops the service.
        """
        await self._async_client.close()
        self.logger.info("%s stopped.", self.__class__.__name__)

    async def _simulate(self) -> None:
        """
        Starts the simulation loop.
        """
        self.logger.info("%s started.", self.__class__.__name__)
        self.logger.info(
            "Simulation time: from %s to %s",
            datetime.fromtimestamp(self.from_),
            datetime.fromtimestamp(self.to),
        )
        self.logger.info("Estimated real time: %s seconds", self.estimate_real_time())
        self._start_time = time.perf_counter()
        iteration = 0

        while True:
            # This iteration should finish executing before the target time
            target_time = self._start_time + iteration * self._time_step

            # Check if the simulation time has reached the end time
            if self.sim_time >= self.to:
                self.logger.info("Simulation time reached the end time.")
                break

            # Dynamically adjust the padding time based on the ratio of planned
            # sleep duration to the actual elapsed time since the last sleep.
            if iteration % self._adjust_freq == 0:
                if (
                    self._just_slept
                    and self._before_sleep is not None
                    and self._planned_sleep_duration is not None
                ):
                    # If we just slept, we need to reset the flag
                    self._just_slept = False
                    # Calculate the time adjustment
                    elapsed_time = time.perf_counter() - self._before_sleep
                    self._sleep_adjustment = self._planned_sleep_duration / elapsed_time

            # Step the simulation time forward
            curr_time = time.perf_counter()
            elapsed_sim_time = (curr_time - self._start_time) * self.speed
            self.sim_time = self.from_ + elapsed_sim_time

            # Emit the TimeStep Event
            self._emit_time_step_event()

            # check if the current time is exceeding the target time
            now = time.perf_counter()
            if now < target_time:
                # We are ahead of the target time, so we need to sleep
                sleep_duration = target_time - now
                if sleep_duration > 0:
                    self._before_sleep = time.perf_counter()
                    self._planned_sleep_duration = sleep_duration
                    await asyncio.sleep(sleep_duration * self._sleep_adjustment)
                    self._just_slept = True

            iteration += 1

    def _emit_time_step_event(self) -> None:
        """
        Emits the TimeStep Event.
        """
        if self._start_time is None:
            self.logger.error("Simulation has not been started yet.")
            return
        event = TimeStepEvent(timestamp=self.sim_time)
        self._async_client.emit_event(event, quite=True)

    async def on_event(self, event: Event) -> None:
        """
        Handles incoming events.
        :param event: The event to handle.
        """
        if isinstance(event, SimStartEvent):
            self._sim_init()
            self._simulation_task = asyncio.create_task(self._simulate())
        elif isinstance(event, SimStopEvent):
            if self._simulation_task:
                self._simulation_task.cancel()
                self._simulation_task = None
            else:
                self.logger.warning("Simulation task is not running.")
