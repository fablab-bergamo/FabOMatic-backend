import logging
import os
from logging.handlers import RotatingFileHandler

import colorlog


def configure_logger(loglevel=logging.DEBUG):
    """
    Configures the logger with the specified log level.

    Args:
        loglevel (int): The log level to set for the logger. Defaults to logging.DEBUG.

    Returns:
        None
    """
    # Create a logger object
    logger = logging.getLogger()
    logger.setLevel(loglevel)

    # Create a formatter for the logs
    formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    # Ensure the log directory is created
    log_dir = os.path.expanduser("~/log")
    os.makedirs(log_dir, exist_ok=True)

    # Create a rotating file handler with a maximum size of 1 MB
    log_file = os.path.join(log_dir, "log.txt")
    file_handler = RotatingFileHandler(log_file, maxBytes=1000000, backupCount=1, encoding="latin-1")
    file_handler.setFormatter(formatter)

    # Add the file handler to the logger object
    logger.addHandler(file_handler)

    # Create a stream handler to log to console
    console_handler = logging.StreamHandler()
    formatter2 = colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red,bg_white",
        },
    )
    console_handler.setFormatter(formatter2)

    # Add the stream handler to the logger object
    logger.addHandler(console_handler)
