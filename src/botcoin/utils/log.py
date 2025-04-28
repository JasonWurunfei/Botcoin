"""This module act a single point of entry for logging configuration."""

import os
import logging

from dotenv import load_dotenv

load_dotenv()

LEVEL = os.getenv("LOG_LEVEL", "DEBUG").upper()
if LEVEL not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
    raise ValueError(
        f"Invalid log level: {LEVEL}. Must be one of DEBUG, INFO, WARNING, ERROR, CRITICAL."
    )

if LEVEL == "DEBUG":
    logging.getLogger().setLevel(logging.DEBUG)
elif LEVEL == "INFO":
    logging.getLogger().setLevel(logging.INFO)

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s: %(message)s"
logging.basicConfig(format=LOG_FORMAT)
