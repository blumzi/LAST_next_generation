import datetime

from utils import Equipment, equipment_ids, init_log, datetime_decoder, DateTimeEncoder, TriState, Never
import socket
from collections import OrderedDict
import json
import logging
from subprocess import Popen
from enum import Enum
import humanize
from driver_interface import DriverInterface
import threading
from fastapi.responses import JSONResponse
import time
import asyncio
import os
import signal
from typing import List


class ReadyMode(Enum):
    Ready = 1
    Routed = 2
    NotAvailable = 3


class ReadyResponse:
    mode: ReadyMode
    message: str


class Request:
    RequestId: int
    Method: str
    Parameters: OrderedDict
    RequestTime: datetime.datetime
    RequestReceived: datetime.datetime


class Response:
    RequestId: int
    Value: str
    Error: str = None
    Exception: str = None
    Timing: {}


class Driver(DriverInterface):
    """
    An object that communicates between a LAST Unit and a device-driver for a specific type of LAST equipment
    using the LIPP (LAST Inter Process Protocol) protocol
    """
    socket: socket              # for communication with the matlab Lipp
    probing_socket: socket      # for periodical probes of the device

    local_socket_path: str
    peer_socket_path: str
    probing_socket_path: str
    current_request_id: int
    _max_bytes = 64 * 1024
    driver_process = None
    pending_request: Request
    _reason: str = None
    equipment_type: Equipment
    equipment_id: int
    equipment_type_and_id: str
    _info: dict
    _responding: TriState = None
    _last_response: datetime.datetime = Never
    _receive_timeout = 5  # seconds
    _ready_timeout = 30  # be patient, matlab needs to come up
    _waiter_for_ready_thread: threading.Thread
    _process_monitor_thread: threading.Thread
    _probing_monitor_thread: threading.Thread
    _terminating = False

    _last_answer_to_probe: datetime.datetime = None
    _answers_to_probe: TriState = None

    lock: threading.Lock
    should_monitor_driver_process: bool = False

    def __init__(self, drivers: list, equipment: Equipment, equipment_id: int = 0):
        super().__init__(equipment, equipment_id)

        drivers[equipment_id] = self

        self.equipment_type = equipment
        self.equipment_type_and_id = self.equipment_type.name.lower()
        if equipment_id in range(1, 5):
            self.equipment_id = equipment_id
            self.equipment_type_and_id += f'-{self.equipment_id}'
            
        self.logger = logging.getLogger(f'lipp-unit-{self.equipment_type_and_id}')
        init_log(self.logger)

        hostname = socket.gethostname()
        if hostname.endswith('e'):
            valid_ids = equipment_ids['e']
        elif hostname.endswith('w'):
            valid_ids = equipment_ids['w']
        else:
            raise Exception("Invalid hostname '{hostname}'")

        if equipment_id != 0 and equipment_id not in valid_ids:
            raise Exception(f"Invalid equipment_id '{equipment_id}', should be one of {valid_ids.__str__()}")
        
        self._info = {
            'Type': 'LIPP',
            'Equipment': self.equipment_type_and_id,
        }

        self.local_socket_path = f'\0lipp-unit-{self.equipment_type_and_id}'
        self.peer_socket_path = self.local_socket_path.replace('unit', 'driver')

        # A socket used for communications with the MATLAB Lipp
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.socket.settimeout(self._ready_timeout)
        self.socket.bind(self.local_socket_path)
        self.current_request_id = 0

        # A socket to receive the results of periodical device probes
        self.probing_socket_path = self.local_socket_path + '-probing'
        self.probing_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.probing_socket.bind(self.probing_socket_path)

        self.cmd = (f"FROM_PYTHON_LIPP=1 exec last-matlab -nodisplay -nosplash -batch \"obs.api.Lipp('EquipmentName'," +
                    f"'{equipment.name.lower()}'")
        if equipment_id != 0:
            self.cmd += f", 'EquipmentId', {equipment_id}"
        self.cmd += ').loop();"'
        self.start_driver_process(reason='first-time')

        self.lock = threading.Lock()

    def start_driver_process(self, reason: str):
        self.logger.info(f">>> Starting driver process, reason='{reason}', cmd='{self.cmd}'")
        self.driver_process = Popen(args=self.cmd, shell=True, preexec_fn=os.setpgrp)
        self.should_monitor_driver_process = True

        self._responding = False
        self._last_response = Never
        
        self._waiter_for_ready_thread = threading.Thread(
            name=f"{self.equipment_type_and_id + '-wait-for-ready-thread'}",
            target=self.wait_for_ready)
        self._waiter_for_ready_thread.start()

        self._process_monitor_thread = threading.Thread(
            name=f"{self.equipment_type_and_id + '-monitor-driver-process-thread'}",
            target=self.monitor_driver_process)
        self._process_monitor_thread.start()

        self._probing_monitor_thread = threading.Thread(
            name=f"{self.equipment_type_and_id + '-monitor-device-probing-thread'}",
            target=self.monitor_device_probing)
        self._probing_monitor_thread.start()

    def end_driver_process(self, reason: str):
        self._terminating = True  # tells threads to die
        if self.driver_process is not None:
            self.logger.info(f">>> Sending SIGTERM to driver process (pid={self.driver_process.pid}), reason='{reason}'")
            self.driver_process.terminate()
            time.sleep(3)
            self.logger.info(f">>> Sending SIGKILL to driver process (pid={self.driver_process.pid}), reason='{reason}'")
            self.driver_process.kill()
        self.driver_process = None
        self.should_monitor_driver_process = False

    def restart_driver_process(self, reason: str):
        self.logger.info(f">>> Restarting driver process, reason='{reason}'")
        self.end_driver_process(reason=reason)
        self.start_driver_process(reason=reason)

    def monitor_driver_process(self):
        """
        Monitors the LIPP (MATLAB) process for this driver
        - Idea: maybe it will restart dead processes using self.cmd (frequent restart handling ?!?)
        """
        while not self._terminating:
            if self.should_monitor_driver_process and self.driver_process is not None:  # still alive
                if self.driver_process.poll() is None:
                    self._info['ProcessId'] = self.driver_process.pid
                else:
                    self._info['ProcessId'] = None
            else:
                self._info['ProcessId'] = None
            time.sleep(5)

    def monitor_device_probing(self):
        while not self._terminating:
            self.receive_probing()  # blocking

    def wait_for_ready(self):
        """
        Waits for a 'ready' packet on the main socket.  This packet will (eventually) arrive when the
         spawned MATLAB process comes-to-life and tries a "Connected = true" on the underlying driver.

        The reply is either 'detected' or 'not-detected' according to whether the driver found its configured hardware.
        """
        self.logger.info("started")
        while not self._terminating:
            incoming_packet = self.receive_from_driver()  # on timeout returns a None incoming_packet

            if incoming_packet is not None:
                self._responding = True
                self.socket.settimeout(self._receive_timeout)  # from now on responses should come faster
                if incoming_packet['Value'] == "not-detected":
                    self.logger.info("not-detected")
                    self._detected = False
                elif incoming_packet['Value'] == "detected":
                    self.logger.info("detected")
                    self._detected = True
                return

        if self._terminating:
            if self.driver_process and self.driver_process.poll() is not None:  # still alive
                try:
                    self.logger.info(f"process pid={self.driver_process.pid} is still alive, killing it!")
                    os.killpg(self.driver_process.pid, signal.SIGKILL)
                    self.logger.info(f"killed process pid={self.driver_process.pid}")
                except ProcessLookupError:
                    pass
                except Exception as ex:
                    self.logger.exception(f"Could not killpg pid={self.driver_process.pid}", ex)

        self.logger.info("done")

    async def get(self, method: str, **kwargs) -> object:
        await asyncio.sleep(0)
        return self.get_or_put(method, **kwargs)
    
    async def put(self, method: str, **kwargs) -> object:
        await asyncio.sleep(0)
        return self.get_or_put(method, **kwargs)

    def get_or_put(self, method: str, **kwargs) -> object:

        if not self.detected:
            return JSONResponse({
                'Error': f"Device '{self.equipment_type_and_id}' not-detected",
            })
        
        request = Request()
        self.current_request_id += 1
        request.RequestId = self.current_request_id
        request.Method = method
        request.Parameters = {}
        for k, v in kwargs.items():
            request.Parameters[k] = v
        request.RequestTime = datetime.datetime.now()
        data = json.dumps(request.__dict__, cls=DateTimeEncoder).encode()
        self.pending_request = request

        response = None
        acquired = self.lock.acquire(timeout=10)
        if acquired:
            try:
                self.socket.sendto(data, self.peer_socket_path)
            except ConnectionRefusedError:
                self._responding = False
                self.lock.release()
                return JSONResponse({
                    'Error': f"LIPP connection to '{self.peer_socket_path[1:]}' refused",
                })

            response = self.receive_from_driver()
            self.lock.release()
        else:
            # did not acquire the lock within 10 seconds, kill the Lipper!
            # self.restart_driver_process(reason=f"did not acquire lock within {10} seconds, " +
            #                                    f"pending request={self.pending_request.__dict__}")
            pass

        return JSONResponse(response)
        # return JSONResponse(response['Value'] if response and 'Value' in response else None)

    def receive_probing(self):
        try:
            data, address = self.probing_socket.recvfrom(self._max_bytes)
        except Exception as ex:
            self.logger.exception(f"While recvfrom probing_socket", exc_info=ex)
            return
        
        self.logger.info(f"got '{data}'" + (f" from '{address}'" if address is not None else ""))
        response = json.loads(data.decode(), object_hook=datetime_decoder)
        if 'AnswersToProbe' not in response:
            self.logger.error(f"Missing 'AnswersToProbe' field in received '{data}'")
            return
        self._answers_to_probe = response['AnswersToProbe']
        self._last_answer_to_probe = datetime.datetime.now()

    def receive_from_driver(self):
        try:
            data, address = self.socket.recvfrom(self._max_bytes)
            self._responding = True
            self._last_response = datetime.datetime.now()
        except socket.timeout:
            # self.logger.error(f"Timeout ({self.socket.gettimeout()} sec.) " +
            #                   f"while recvfrom on '{self.peer_socket_path[1:]}'")
            self._responding = False
            return None

        self.logger.info(f"got '{data}'" + f" from '{address}'" if address is not None else "")
        response = json.loads(data.decode(), object_hook=datetime_decoder)

        if 'Error' in response and response['Error'] is not None:
            self.logger.error(f"remote Error=\'{response['Error']}\'")

        elif 'Exception' in response and response['Exception'] is not None:
            self.logger.error("remote (MATLAB) Exception:")
            ex = response['Exception']
            self.logger.error(f"remote   Exception: {ex['identifier']}")
            self.logger.error(f"remote     Message: {ex['message']}")
            self.logger.error(f"remote       Cause: {ex['cause']}")
            self.logger.error(f"remote  Correction: {ex['Correction']}")
            self.logger.error(f"remote       Stack:")
            if isinstance(ex['stack'], list):
                for st in ex['stack']:
                    self.logger.error(f"remote [{st['file']}:{st['line']}] {st['name']}")
            elif isinstance(ex['stack'], dict):
                self.logger.error(f"remote [{ex['stack']['file']}:{ex['stack']['line']}] {ex['stack']['name']}")
        elif 'RequestId' not in response or response['RequestId'] is None:
            raise Exception("Missing 'RequestId' in response")
        elif response['RequestId'] != self.current_request_id:
            raise Exception(f"expected RequestId '{self.current_request_id}' got '{response['RequestId']}'")

        if 'Timing' in response and response['Timing'] is not None:
            tx = response['Timing']['Request']
            rx = response['Timing']['Response']
            tx_duration = tx['Received'] - tx['Sent']
            rx['Received'] = datetime.datetime.now()
            rx_duration: datetime.timedelta = (rx['Received'] - rx['Sent'])
            elapsed = rx['Received'] - tx['Sent']
            self.logger.info(f", Timing: elapsed: {humanize.precisedelta(elapsed, minimum_unit='microseconds')}, " +
                             f"request: {humanize.precisedelta(tx_duration, minimum_unit='microseconds')}, " +
                             f"response: {humanize.precisedelta(rx_duration, minimum_unit='microseconds')}")

        return response

    def __del__(self):
        self.end_driver_process(reason='destructor')
        if self.socket:
            self.socket.close()
        return self._reason
    
    async def quit(self):
        if self._detected and self.driver_process is not None:
            self.logger.info(f"quit: Sending method='quit' to pid={self.driver_process.pid}")
            await self.get(method='quit')
        self.end_driver_process(reason='quit')
    
    def info(self):
        return self._info
    
    def status(self):
        return {
            'AnswersToProbe': self._answers_to_probe,
            'LastAnswerToProbe': self._last_answer_to_probe,
        }
    
    @property
    def detected(self) -> bool:
        """Was the actual device detected?"""
        return self._detected
    
    def detected_setter(self, value: bool):
        self._detected = value

    @property
    def responding(self) -> bool:
        return self._responding
    
    @property
    def last_response(self):
        return self._last_response


if __name__ == '__main__':
    drivers_list: List[Driver] = list()
    driver = Driver(drivers=drivers_list, equipment=Equipment.Test, equipment_id=3)

    ready_packet = driver.receive_from_driver()
    driver.logger.info(f"received ready packet with mode={ready_packet.mode}")

    if ready_packet['Value'] == "ready":
        driver.get(method='status')
        driver.get(method='slewToCoordinates', ra=1.2, dec=3.4)
        driver.get(method='move', position=10234)

    driver.get(method='quit')
