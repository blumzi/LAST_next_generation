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
    Response: str
    Error: str = None
    ErrorReport: str = None
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
    _available: bool = False
    _reason: str = None
    state: DriverState = DriverState.Unknown
    equipment: Equipment
    equipment_id: int
    equip: str
    thread = None

    def __init__(self, drivers_list: list, equipment: Equipment, equipment_id: int = 0):
        self.state = DriverState.Initializing

        drivers_list[equipment_id] = self

        self.equipment = equipment
        self.equip = self.equipment.name.lower()
        if equipment_id is not None:
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

        self.local_socket_path = f'\0lipp-unit-{self.equip}'
        self.peer_socket_path = self.local_socket_path.replace('unit', 'driver')

        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.socket.bind(self.local_socket_path)
        self.current_request_id = 0

        cmd=f"matlab -nodisplay -nosplash -batch \"obs.api.Lipp('EquipmentName', '{equipment.name.lower()}'"
        if equipment_id != 0:
            cmd += f", 'EquipmentId', {equipment_id}"
        cmd += ').loop();"'
        self.logger.info(f'Spawning "{cmd}"')
        self.driver_process = Popen(args=cmd, stderr=DEVNULL, shell=True)
        
        threading.Thread(name=f"{self.equip + '-wait-for-ready-thread'}", target=self.wait_for_ready).start()

    def wait_for_ready(self):
        self.logger.info(f"waiting for ready packet ...")
        ready_packet = self.receive()
        reason = f"MATLAB driver reports '{self.equip} is "
        if ready_packet['Response'] == "unavailable":
            reason += "'unavailable'"
            self.logger.info('wait_for_ready: ' + reason)
            self._available = False
            self._reason = reason
            self.state = DriverState.Unavailable
        elif ready_packet['Response'] == "ready":
            self._available = True
            self._reason = None
            self.logger.info('wait_for_ready: ' + reason + "'available'")
            self.state = DriverState.Available

    async def device_not_available(self):
        return JSONResponse({
            'Response': None,
            'Error': f"Device '{self.equip}' not available, state={self.state}",
            'Reason': self._reason,
        })

    def get(self, method: str, **kwargs) -> object:
        if not self.state == DriverState.Available:
            return self.device_not_available()
        
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
        self.socket.sendto(data, self.peer_socket_path)

        return self.receive()
    
    def put(self, method: str, **kwargs) -> object:
        if not self.state == DriverState.Available:
            return self.device_not_available()
        
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
        self.socket.sendto(data, self.peer_socket_path)

        return self.receive()

    def receive(self) -> dict:
        data, address = self.socket.recvfrom(self._max_bytes)
        # self.logger.info(f"receive: got '{data}' from '{address}")
        response = json.loads(data.decode(), object_hook=datetime_decoder)

        if 'RequestId' in response and response['RequestId'] is not None:
            if response['RequestId'] != self.current_request_id:
                raise Exception(f"expected RequestId '{self.current_request_id}' got '{response['RequestId']}'")
        else:
            raise Exception("Missing 'RequestId' in response")

        msg = None
        if 'Error' in response and response['Error'] is not None:
            self.logger.error(f"lipp-receive: remote Error=\'{response['Error']}\'")

        # self.logger.info(f">>>{address}<<<, >>>{data}<<<")
        if 'Exception' in response and response['Exception'] is not None:
            ex = response['Exception']
            self.logger.error(f"remote   Exception: {ex['identifier']}")
            self.logger.error(f"remote     Message: {ex['message']}")
            self.logger.error(f"remote       Cause: {ex['cause']}")
            self.logger.error(f"remote  Correction: {ex['Correction']}")
            self.logger.error(f"remote       Stack:")
            for i in range(len(ex['stack'])):
                st = ex['stack'][i]
                self.logger.error(f"remote             {i:2}. [{st['file']}:{st['line']}] {st['name']}")


        if 'Timing' in response and response['Timing'] is not None:
            tx = response['Timing']['Request']
            rx = response['Timing']['Response']
            tx_duration = tx['Received'] - tx['Sent']
            rx['Received'] = datetime.datetime.now()
            rx_duration: datetime.timedelta = (rx['Received'] - rx['Sent'])
            elapsed = rx['Received'] - tx['Sent']
            msg += (f", Timing: elapsed: {humanize.precisedelta(elapsed, minimum_unit='microseconds')}, " +
                    f"request: {humanize.precisedelta(tx_duration, minimum_unit='microseconds')}, " + 
                    f"response: {humanize.precisedelta(rx_duration, minimum_unit='microseconds')}")
        
        if msg:
            self.logger.info(msg)

        return response

    def __del__(self):
        if self.driver_process:
            self.driver_process.terminate()
        if self.socket:
            self.socket.close()

    def available(self) -> bool:
        return self._available
    
    def reason_for_not_available(self) -> str:
        return self._reason


class DeviceUnavailable(BaseModel):
    reason: str

    def __init__(self, reason: str):
        self.reason = reason

    def __await__(self):
        return {
            'Response': None,
            'Error': f"Device not available ({self.reason})"
        }
    
if __name__ == '__main__':
    driver = Driver(equipment=Equipment.Test, equipment_id=3)

    ready_packet = driver.receive()
    driver.logger.info(f"received ready packet with mode={ready_packet.mode}")

    if ready_packet['Response'] == "ready":
        driver.get(method='status')
        driver.get(method='slewToCoordinates', ra=1.2, dec=3.4)
        driver.get(method='move', position=10234)

    driver.get(method='quit')
