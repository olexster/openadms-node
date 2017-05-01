#!/usr/bin/env python3
"""
Copyright (c) 2017 Hochschule Neubrandenburg.

Licenced under the EUPL, Version 1.1 or - as soon they will be approved
by the European Commission - subsequent versions of the EUPL (the
"Licence");

You may not use this work except in compliance with the Licence.

You may obtain a copy of the Licence at:

    https://joinup.ec.europa.eu/community/eupl/og_page/eupl

Unless required by applicable law or agreed to in writing, software
distributed under the Licence is distributed on an "AS IS" basis,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the Licence for the specific language governing permissions and
limitations under the Licence.
"""

"""The module class to bundle a worker with a messenger."""

__author__ = 'Philipp Engel'
__copyright__ = 'Copyright (c) 2017 Hochschule Neubrandenburg'
__license__ = 'EUPL'

import logging
import queue
import threading

from typing import *


class Module(threading.Thread):
    """
    Module bundles a worker with a messenger and manages the communication
    between them.
    """

    def __init__(self, messenger, worker):
        threading.Thread.__init__(self, name=worker.name)
        self.logger = logging.getLogger(worker.name)
        self.daemon = True

        self._messenger = messenger                 # MQTT messenger.
        self._worker = worker                       # Worker instance.

        self._inbox = queue.Queue()                 # Message inbox.
        self._topic = self._messenger.topic         # MQTT topic to listen to.

        # Set the callback functions of the messenger and the worker.
        self._messenger.downlink = self.retrieve    # Call on new messages.
        self._worker.uplink = self.publish          # Call to publish message.

        # Subscribe to the worker's name.
        self._messenger.subscribe(self._topic + '/' + worker.name)

    def publish(self, target: str, message: str) -> None:
        """Sends an `Observation` object to the next receiver by using the
        messenger.

        Args:
            target (str): Name of the topic.
            message (str): Message in JSON format.
        """
        target_path = '{}/{}'.format(self._topic, target)
        self._messenger.publish(target_path, message)

    def retrieve(self, message: List[Dict]) -> None:
        """Callback function for the messenger. New data from the message broker
        lands here.

        Args:
            message (List): Header and payload of the message, both Dict.
        """
        self._inbox.put(message)

    def run(self) -> None:
        """Checks the inbox for new messages and calls the `handle()` method of
        the worker for further processing. Runs within a thread."""
        self._worker.is_running = True

        self.logger.debug('Connecting module "{}" to {}:{} ...'
                          .format(self._worker.name,
                                  self._messenger.host,
                                  self._messenger.port))
        self._messenger.connect()

        while True:
            message = self._inbox.get()   # Blocking I/O.
            self._worker.handle(message)  # Fire and forget.

        self._messenger.disconnect()

    def start_worker(self) -> None:
        self._worker.is_running = True

    def stop_worker(self) -> None:
        self._worker.is_running = False

    @property
    def messenger(self) -> Any:
        return self._messenger

    @property
    def topic(self) -> str:
        return self._topic

    @property
    def worker(self) -> Any:
        return self._worker

    @messenger.setter
    def messenger(self, messenger: Any) -> None:
        self._messenger = messenger

    @worker.setter
    def worker(self, worker: Any) -> None:
        self._worker = worker
