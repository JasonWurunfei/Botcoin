"""This module act a single point of entry for logging configuration."""

import logging

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s: %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
