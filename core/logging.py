#!/usr/bin/env python3.6

"""Various data structures, filters, formatters, and handlers for logging."""

__author__ = 'Philipp Engel'
__copyright__ = 'Copyright (c) 2017 Hochschule Neubrandenburg'
__license__ = 'BSD-2-Clause'

import logging

from collections import deque
from typing import Any


class RootFilter(logging.Filter):
    """
    RootFilter is a helper class to filter unwanted log messages from external
    Python modules.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Returns whether a logging.LogRecord should be logged."""
        if record.name.startswith(('asyncio',
                                   'hbmqtt',
                                   'passlib',
                                   'urllib3',
                                   'transitions')):
            return False

        return True


class RingBuffer:
    """
    RingBuffer stores elements in a deque. It is a FIFO list with fixed size to
    cache a number of elements, like log messages. The oldest elements get
    removed when the number of elements is greater than the maximum length.
    """

    def __init__(self, max_length: int):
        """
        Args:
            max_length: The maximum size of the deque.
        """
        self._deque = deque(maxlen=max_length)

    def __len__(self):
        return len(self._deque)

    def append(self, x: Any) -> None:
        """Appends an element to the deque.

        Args:
            x: Element to append.
        """
        self._deque.append(x)

    def list(self) -> Any:
        return list(self._deque)

    def pop(self) -> Any:
        """Pops an element.

        Returns:
            String on the left side of the deque.
        """
        return self._deque.popleft()

    def to_string(self) -> str:
        """Returns the whole deque as a string.

        Returns:
            String containing all string elements in the deque.
        """
        return '\n'.join(list(self._deque))


class StringFormatter(logging.Formatter):
    """
    StringFormatter simply returns a formatted string of a log record.
    """

    def __init__(self):
        super().__init__()
        self.datefmt = '%Y-%m-%dT%H:%M:%S'

    def format(self, record: logging.LogRecord) -> str:
        """Return formatted string of log record.

        Args:
            record: The log record.

        Returns:
            Formatted string of log record.
        """
        try:
            record.asctime
        except AttributeError:
            record.asctime = self.formatTime(record, self.datefmt)

        try:
            record.message
        except AttributeError:
            record.message = record.msg

        s = '{} - {:>8} - {:>26} - {}'.format(record.asctime,
                                              record.levelname,
                                              record.name,
                                              record.message)

        return s


class RingBufferLogHandler(logging.Handler):
    """
    RingBufferLogHandler stores a number of log messages in a `RingBuffer`.
    """

    def __init__(self, level: int, size: int):
        """
        Args:
            level: The log level.
            size: The size of the `RingBuffer`.
        """
        super().__init__(level)

        self._size = size
        self._buffer = RingBuffer(self._size)

    def emit(self, record: logging.LogRecord) -> None:
        """Adds a log record to the internal ring buffer.

        Args:
            record: The log record.
        """
        if record:
            log_entry = self.format(record)
            self._buffer.append(log_entry)

    def get_logs(self) -> str:
        """Returns all log messages as a concatenated string.

        Returns:
            All log messages.
        """
        return self._buffer.to_string()

    @property
    def buffer(self) -> RingBuffer:
        return self._buffer

    @property
    def size(self) -> int:
        return self._size
