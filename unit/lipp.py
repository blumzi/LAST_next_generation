import datetime

from utils import Equipment, equipment_ids, init_log, datetime_decoder, DateTimeEncoder, DriverState
import socket
from collections import OrderedDict
import json
import logging
from subprocess import Popen, DEVNULL
from enum import Enum
import humanize
from driver_interface import DriverInterface
import threading
from pydantic import BaseModel
from fastapi.responses import JSONResponse
import time
import asyncio

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
    socket: socket
    local_socket_path: str
    peer_socket_path: str
    current_request_id: int
    _max_bytes = 64 * 1024
    driver_process = None
    pending_request: Request
    _reason: str = None
    _state: DriverState = DriverState.Unknown
    equipment: Equipment
    equipment_id: int
    equip: str
    _info: dict

    def __init__(self, drivers_list: list, equipment: Equipment, equipment_id: int = 0):
        self._state = DriverState.Initializing

        drivers_list[equipment_id] = self

        self.equipment = equipment
        self.equip = self.equipment.name.lower()
        if equipment_id in range(1,5):
            self.equipment_id = equipment_id
            self.equip += f'-{self.equipment_id}'
            
        self.logger = logging.getLogger(f'lipp-unit-{self.equip}')
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
            'Equipment': self.equip,
        }

        self.local_socket_path = f'\0lipp-unit-{self.equip}'
        self.peer_socket_path = self.local_socket_path.replace('unit', 'driver')

        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.socket.bind(self.local_socket_path)
        self.current_request_id = 0

        cmd=f"FROM_PYTHON_LIPP=1 last-matlab -nodisplay -nosplash -batch \"obs.api.Lipp('EquipmentName', '{equipment.name.lower()}'"
        if equipment_id != 0:
            cmd += f", 'EquipmentId', {equipment_id}"
        cmd += ').loop();"'
        self.logger.info(f'Spawning "{cmd}"')
        self.driver_process = Popen(args=cmd, stderr=DEVNULL, shell=True)
        
        threading.Thread(name=f"{self.equip + '-wait-for-ready-thread'}", target=self.wait_for_ready).start()
        threading.Thread(name=f"{self.equip + '-monitor-thread'}", target=self.process_monitor).start()

    def process_monitor(self):
        """
        Monitors the LIPP (MATLAB) process for this driver
        - Idea: maybe it will restart dead processes (frequent restart handling ?!?)
        """
        while True:
            if self.driver_process is not None:  # still alive
                if self.driver_process.poll() is None:
                    self._info['ProcessId'] = self.driver_process.pid
                else:
                    self._info['ProcessId'] = None
            else:
                self._info['ProcessId'] = None
            time.sleep(5)

    def wait_for_ready(self):
        self.logger.info(f"waiting for ready packet ...")
        ready_packet = self.receive()
        reason = f"MATLAB driver reports '{self.equip} is "
        if ready_packet['Value'] == "unavailable":
            reason += "'unavailable'"
            self.logger.info('wait_for_ready: ' + reason)
            self._reason = reason
            self._state = DriverState.Unavailable
        elif ready_packet['Value'] == "available":
            self._reason = None
            self.logger.info("wait_for_ready: 'available'")
            self._state = DriverState.Available

    async def device_not_available(self):
        await asyncio.sleep(0)
        return JSONResponse({
            'Error': f"Device '{self.equip}' not available, state={self._state}, reason={self._reason}",
        })
    
    async def connection_refused(self):
        await asyncio.sleep(0)
        return JSONResponse({
            'Error': f"LIPP connection to '{self.peer_socket_path[1:]}' refused",
        })

    async def get(self, method: str, **kwargs) -> object:
        await asyncio.sleep(0)

        # if not self._state == DriverState.Available:
        #     return self.device_not_available()
        
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
        try:
            self.socket.sendto(data, self.peer_socket_path)
        except ConnectionRefusedError:
            return self.connection_refused()

        response = self.receive()
        return response['Value']
    
    async def put(self, method: str, **kwargs) -> object:
        await asyncio.sleep(0)

        # if not self._state == DriverState.Available:
        #     return self.device_not_available()
        
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
        try:
            self.socket.sendto(data, self.peer_socket_path)
        except ConnectionRefusedError:
            return self.connection_refused()

        response = self.receive()
        return response['Value']

    def receive(self):
        label = "lipp.receive: "
        data, address = self.socket.recvfrom(self._max_bytes)
        self.logger.info(label + f"got '{data}' from '{address}")
        response = json.loads(data.decode(), object_hook=datetime_decoder)

        if 'Error' in response and response['Error'] is not None:
            self.logger.error(label + f"remote Error=\'{response['Error']}\'")

        elif 'Exception' in response and response['Exception'] is not None:
            self.logger.error(label + "remote (MATLAB) Exception:")
            ex = response['Exception']
            self.logger.error(f"remote   Exception: {ex['identifier']}")
            self.logger.error(f"remote     Message: {ex['message']}")
            self.logger.error(f"remote       Cause: {ex['cause']}")
            self.logger.error(f"remote  Correction: {ex['Correction']}")
            self.logger.error(f"remote       Stack:")
            if type(ex['stack']) == list:
                for st in ex['stack']:
                    self.logger.error(f"remote [{st['file']}:{st['line']}] {st['name']}")
            elif type(ex['stack']) == dict:
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
            self.logger.info(label + f", Timing: elapsed: {humanize.precisedelta(elapsed, minimum_unit='microseconds')}, " +
                    f"request: {humanize.precisedelta(tx_duration, minimum_unit='microseconds')}, " + 
                    f"response: {humanize.precisedelta(rx_duration, minimum_unit='microseconds')}")

        return response

    def __del__(self):
        if self.driver_process:
            self.driver_process.terminate()
        if self.socket:
            self.socket.close()
        return self._reason
    
    def info(self):
        return self._info
    
    def status(self):
        pass

    def state(self) -> DriverState:
        return self._state


class DeviceUnavailable(BaseModel):
    reason: str

    def __init__(self, reason: str):
        self.reason = reason

    def __await__(self):
        return {
            'Error': f"Device not available (reason={self.reason})"
        }
    
if __name__ == '__main__':
    driver = Driver(equipment=Equipment.Test, equipment_id=3)

    ready_packet = driver.receive()
    driver.logger.info(f"received ready packet with mode={ready_packet.mode}")

    if ready_packet['Value'] == "ready":
        driver.get(method='status')
        driver.get(method='slewToCoordinates', ra=1.2, dec=3.4)
        driver.get(method='move', position=10234)

    driver.get(method='quit')
