import logging
import os


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    log_level = os.getenv("LOG_LEVEL")
    logger.setLevel(log_level if log_level else logging.INFO)
    logger.addHandler(logging.StreamHandler())
    return logger
