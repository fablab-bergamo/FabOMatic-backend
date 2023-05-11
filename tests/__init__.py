from logging.handlers import RotatingFileHandler
from .test_database import *
import logging


def configure_logger():
    # Create a logger object
    logger = logging.getLogger('test_logger')
    logger.setLevel(logging.DEBUG)

    # Create a formatter for the logs
    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    # Create a rotating file handler with a maximum size of 1 MB
    log_file = os.path.join(os.path.dirname(__file__), 'test-log.txt')
    file_handler = RotatingFileHandler(
        log_file, maxBytes=1000000, backupCount=1, encoding='latin-1')
    file_handler.setFormatter(formatter)

    # Add the file handler to the logger object
    logger.addHandler(file_handler)


configure_logger()
