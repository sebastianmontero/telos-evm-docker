#!/usr/bin/env python3

import time
import logging

from dockerstack.logging import DockerStackLogger


class Formatter(logging.Formatter):

    COLORS = {
        'TEVMC_INFO': '\033[95m',     # Blue
        'TEVMC_WARNING': '\033[93m',  # Yellow
        'TEVMC_ERROR': '\033[91m',    # Red
    }

    RESET = '\033[0m'

    _DISPLAY = {
        'TEVMC_INFO': 'info',
        'TEVMC_WARNING': 'warning',
        'TEVMC_ERROR': 'error'
    }

    def __init__(self):
        super().__init__('%(asctime)s %(message)s', '%Y-%m-%d %H:%M:%S')
        self.converter = time.gmtime

    def format(self, record):
        if len(record.funcName) < 20:
            padding_length = 20 - len(record.funcName)
            record.funcName = record.funcName[:20] + ' ' * padding_length
        else:
            record.funcName = record.funcName[:20]
        log_message = super().format(record)
        levelname = record.levelname
        if levelname not in self.COLORS:
            return log_message
        return f"{self.COLORS[levelname]}{self._DISPLAY[levelname]}{self.RESET} : {log_message}"


INFO_NUM = logging.getLevelName('INFO')
WARNING_NUM = logging.getLevelName('WARNING')
ERROR_NUM = logging.getLevelName('ERROR')

# Define custom log levels
TEVMC_INFO_NUM = 25
TEVMC_WARNING_NUM = 35
TEVMC_ERROR_NUM = 45


logging.addLevelName(TEVMC_INFO_NUM, 'TEVMC_INFO')
logging.addLevelName(TEVMC_WARNING_NUM, 'TEVMC_WARNING')
logging.addLevelName(TEVMC_ERROR_NUM, 'TEVMC_ERROR')


class TEVMCLogger(DockerStackLogger):

    def info(self, message, *args, **kwargs):
        if self.isEnabledFor(INFO_NUM):
            self._log(TEVMC_INFO_NUM, message, args, **kwargs)

    def warning(self, message, *args, **kwargs):
        if self.isEnabledFor(WARNING_NUM):
            self._log(TEVMC_WARNING_NUM, message, args, **kwargs)

    def error(self, message, *args, **kwargs):
        if self.isEnabledFor(ERROR_NUM):
            self._log(TEVMC_ERROR_NUM, message, args, **kwargs)

    def stack_info(self, message, *args, **kwargs):
        if self.isEnabledFor(TEVMC_INFO_NUM):
            self._log(TEVMC_INFO_NUM, message, args, **kwargs)

    def stack_warning(self, message, *args, **kwargs):
        if self.isEnabledFor(TEVMC_WARNING_NUM):
            self._log(TEVMC_WARNING_NUM, message, args, **kwargs)

    def stack_error(self, message, *args, **kwargs):
        if self.isEnabledFor(TEVMC_ERROR_NUM):
            self._log(TEVMC_ERROR_NUM, message, args, **kwargs)


def get_tevmc_logger(level: str) -> TEVMCLogger:
    # Set the logger class to DockerStackLogger
    logging.setLoggerClass(TEVMCLogger)

    # Check if root logger is already initialized
    if logging.root.handlers:
        logging.root.handlers = []

    # Directly set the class of the root logger
    logging.root.__class__ = TEVMCLogger

    # Setup the root logger
    logger = logging.getLogger()
    handler = logging.StreamHandler()
    handler.setFormatter(Formatter())
    logger.addHandler(handler)
    logger.setLevel(level.upper())

    logger.propagate = False
    logging.getLogger().addHandler(logging.NullHandler())

    assert isinstance(logger, TEVMCLogger)

    return logger
