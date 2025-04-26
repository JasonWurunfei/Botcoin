"""This module act a single point of entry for logging configuration."""

import os
import logging

from dotenv import load_dotenv

load_dotenv()

LEVEL = os.getenv("LOG_LEVEL", "DEBUG").upper()

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s: %(message)s"
logging.basicConfig(level=LEVEL, format=LOG_FORMAT)
