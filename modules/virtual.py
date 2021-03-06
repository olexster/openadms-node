#!/usr/bin/env python3.6

"""Module for virtual sensors."""

__author__ = 'Philipp Engel'
__copyright__ = 'Copyright (c) 2017 Hochschule Neubrandenburg'
__license__ = 'BSD-2-Clause'

import math
import random
import re
import time

import arrow

from core.manager import Manager
from core.observation import Observation
from core.prototype import Prototype


class VirtualSensor(Prototype):
    """
    VirtualSensor is a prototype class for virtual sensors.
    """

    def __init__(self, module_name: str, module_type: str, manager: Manager):
        super().__init__(module_name, module_type, manager)
        self.patterns = {}

    def process_observation(self, obs: Observation) -> Observation:
        request_sets = obs.get('requestSets')

        for set_name, request_set in request_sets.items():
            request = request_set.get('request')
            timeout = request_set.get('timeout')
            sleep_time = request_set.get('sleepTime')
            response = ''

            self.logger.verbose(f'Sending request "{set_name}" to sensor '
                                f'"{obs.get("sensorName")}" on virtual port '
                                f'"{self.name}"')

            for pattern in self.patterns:
                reg_exp = re.compile(pattern)
                parsed = reg_exp.match(request)

                if not parsed:
                    continue

                response = self.patterns[pattern](request)

                self.logger.verbose(f'Received response '
                                    f'"{self.sanitize(response)}" from sensor '
                                    f'"{obs.get("sensorName")}" on virtual '
                                    f'port "{self.name}"')
                break

            request_set['response'] = response
            time.sleep((timeout * 0.25) + sleep_time)

        obs.set('portName', self._name)
        obs.set('timestamp', str(arrow.utcnow()))

        return obs

    def sanitize(self, s: str) -> str:
        """Escapes some non-printable characters in a given string.

        Args:
            s: The string to sanitize.

        Returns:
            The sanitized string.
        """
        return s.replace('\n', '\\n')\
                .replace('\r', '\\r')\
                .replace('\t', '\\t')\
                .strip()


class VirtualTotalStationTM30(VirtualSensor):
    """
    VirtualTotalStationTM30 simulates the Leica TM30 totalstation by processing
    GeoCOM commands.
    """

    def __init__(self, module_name: str, module_type: str, manager: Manager):
        super().__init__(module_name, module_type, manager)

        self.patterns = {
            '%R1Q,5003:\\r\\n': self.get_sensor_id,
            '%R1Q,5004:\\r\\n': self.get_sensor_name,
            '%R1Q,9027:(-?[0-9]*\.?[0-9]+),(-?[0-9]*\.?[0-9]+),2,1,0\\r\\n':
                self.set_direction,
            '%R1Q,2008: 1,1\\r\\n': self.measure_distance,
            '%R1Q,2167: 5000,1\\r\\n': self.do_complete_measurement
        }

    def do_complete_measurement(self, request: str) -> str:
        """Does a complete measurement of slope distance, horizontal direction,
        and vertical angle to a target. The values are randomly selected within
        boundaries. Just a quick and dirty approach to get fake sensor data.

        Args:
            request: GeoCOM request string.

        Returns:
            GeoCOM string with encapsulated sensor data.
        """
        return_code = '0'
        hz = '{:0.15f}'.format(random.uniform(0, 2 * math.pi))
        v = '{:0.15f}'.format(random.uniform(1, 2))
        acc_angle = '{:0.15f}'.format(random.uniform(-1, 1) * 10e-6)
        c = '{:0.15f}'.format(random.uniform(-1, 1) * 10e-5)
        l = '{:0.15f}'.format(random.uniform(-1, 1) * 10e-5)
        acc_incl = '{:0.15f}'.format(random.uniform(-1, 1) * 10e-6)
        slope_dist = '{:0.15f}'.format(random.uniform(1, 2000))
        dist_time = '{:8.0f}'.format(random.uniform(4, 5) * 10e8)

        response = (f'%R1P,0,0:{return_code},{hz},{v},{acc_angle},{c},{l},'
                    f'{acc_incl},{slope_dist},{dist_time}\r\n')
        return response

    def get_sensor_id(self, request: str) -> str:
        """Returns the sensor id.

        Args:
            request: GeoCOM request string.

        Returns:
            GeoCOM string with encapsulated sensor id.
        """
        return_code = '0'
        response = f'%R1P,0,0:{return_code},999999\r\n'
        return response

    def get_sensor_name(self, request: str) -> str:
        """Returns the sensor name.

        Args:
            request: GeoCOM request string.

        Returns:
            GeoCOM string with encapsulated sensor name.
        """
        return_code = '0'
        response = f'%R1P,0,0:{return_code},"TM30 0.5"\r\n'
        return response

    def measure_distance(self, request: str) -> str:
        """Returns the return code for distance measurement.

        Args:
            request: GeoCOM request string.

        Returns:
            GeoCOM string with return code.
        """
        return_code = '0'
        response = '%R1P,0,0:{}\r\n'.format(return_code)
        return response

    def set_direction(self, request: str) -> str:
        """Returns the return code for direction setting.

        Args:
            request: GeoCOM request string.

        Returns:
            GeoCOM string with return code.
        """
        return_code = '0'
        response = f'%R1P,0,0:{return_code}\r\n'
        return response


class VirtualDTM(VirtualSensor):
    """
    VirtualDTM simulates the STS DTM meteorological sensor.
    """

    def __init__(self, module_name: str, module_type: str, manager: Manager):
        super().__init__(module_name, module_type, manager)

        self.patterns = {
            'A\\r': self.power_on,
            'CMDT 1\\r': self.set_command_set,
            'SAVE\\r': self.save,
            'PRES \?\\r': self.get_pressure,
            'TEMP \?\\r': self.get_temperature
        }

    def get_pressure(self, request: str) -> str:
        """Returns pressure value between 980 and 1150 hPa.

        Args:
            request: Request string.

        Returns:
            String with pressure value.
        """
        high = 1150
        low = 980

        return '+{:06.1f}\r'.format(random.uniform(low, high))

    def get_temperature(self, request: str) -> str:
        """Returns temperature value between -20 and 40 °C.

        Args:
            request: Request string.

        Returns:
            String with temperature value.
        """
        high = 40
        low = -20

        t = random.uniform(low, high)

        if t < 0:
            return '{:07.1f}\r'.format(t)
        else:
            return '+{:06.1f}\r'.format(t)

    def power_on(self, request: str) -> str:
        """Simulates power-on.

        Args:
            request: Request string.

        Returns:
            Response string.
        """
        return '#\r'

    def save(self, request: str) -> str:
        """Simulates saving of changes.

        Args:
            request: Request string.

        Returns:
            Response string.
        """
        return '*\r'

    def set_command_set(self, request: str) -> str:
        """Simulates change of command set.

        Args:
            request: Request string.

        Returns:
            Response string.
        """
        return '*\r'


class VirtualIndicatorOne(VirtualSensor):
    """
    VirtualIndicatorOne simulates the Sylvac S_Dial One digital
    indicator/extensometer.
    """

    def __init__(self, module_name: str, module_type: str, manager: Manager):
        super().__init__(module_name, module_type, manager)

        self._current_value = 0.0
        self.patterns = {
            '\?\r': self.get_distance
        }

    def get_distance(self, request: str) -> str:
        """Returns fake distance.

        Args:
            request: Request string.

        Returns:
            Response string with distance.
        """
        x = (1.0 + math.sin(self._current_value)) * 12.5
        self._current_value += 0.25

        return '{:7.3f}\r'.format(x)
