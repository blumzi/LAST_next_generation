import datetime

from utils import Equipment, equipment_ids, init_log, datetime_decoder, DateTimeEncoder
import socket
from collections import OrderedDict
import json
import logging
from subprocess import Popen
import os
from enum import Enum


class LIPPRequest:
    RequestId: int
    Method: str
    Parameters: OrderedDict
    RequestTime: datetime.datetime


class LIPPTiming:
    Sent: datetime.datetime
    Received: datetime.datetime


class Timing:
    Request: LIPPTiming
    Response: LIPPTiming


class LIPPResponse:
    RequestId: int
    Response: str
    Error: str = None
    ErrorReport: str = None
    Timing: Timing

class LIPPReady:
    Status: str

class Lipper:
    """
    An object that communicates between a LAST Unit and a device-driver for a specific type of LAST equipment
    using the LIPP (LAST Inter Process Protocol) protocol
    """
    socket_to_driver: socket.socket
    socket_path: str
    current_request_id: int
    _max_bytes = 64 * 1024
    driver_process = None
    pending_request: None

    def __init__(self, equipment: Equipment, equipment_id: int | None):
        logger_name = f'lipp-{equipment.name}'
        if equipment_id is not None:
            logger_name += f'-{equipment_id}'
        logger_name += '-unit'
        self.logger = logging.getLogger(logger_name)
        init_log(self.logger)

        hostname = socket.gethostname()
        if not hostname.startswith('last'):
            hostname = 'last07e'
        if hostname.endswith('e'):
            valid_ids = equipment_ids['e']
        elif hostname.endswith('w'):
            valid_ids = equipment_ids['w']
        else:
            raise f"Invalid hostname '{hostname}'"

        if equipment_id not in valid_ids:
            raise f"Invalid equipment_id, should be one of {str.join(valid_ids, ', ')}"

        self.socket_path = f'\0lipp-{equipment.name}'
        if equipment_id is not None:
            self.socket_path += f'-{equipment_id}'

        self.socket_to_driver = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.socket_to_driver.bind(self.socket_path)
        self.current_request_id = -1

        self.driver_process = Popen(args=f'python3.12 -m lipp-simulator --socket {self.socket_path[1:]}',
                                    cwd=os.path.curdir,
                                    shell=True)

    def call(self, method: str, **kwargs):
        request = LIPPRequest()
        self.current_request_id += 1
        request.RequestId = self.current_request_id
        request.Method = method
        request.Parameters = {}
        for k, v in kwargs.items():
            request.Parameters[k] = v
        request.RequestTime = datetime.datetime.now()
        data = json.dumps(request.__dict__, cls=DateTimeEncoder).encode()
        # self.logger.info(f"sending '{data}' on '{self.socket_path[1:]}'")
        self.pending_request = request
        self.socket_to_driver.sendto(data, self.socket_path)

        response = self.receive()
        self.logger.info(f"request: '{request.__dict__}' ==> response: {response}")



    def receive(self) -> object:
        data, address = self.socket_to_driver.recvfrom(self._max_bytes)
        # self.logger.info(f"received: '{data}'")
        response = json.loads(data.decode(), object_hook=datetime_decoder)

        if 'RequestId' in response and response['RequestId'] is not None:
            if response['RequestId'] != self.current_request_id:
                raise Exception(f"expected RequestId '{self.current_request_id}' got '{response['RequestId']}'")
        else:
                raise Exception("Missing 'RequstId' in response")

        msg = None
        if 'Error' in response and response['Error'] is not None:
            msg = response['Error']
            if response['ErrorReport'] is not None:
                msg += f" - {response['ErrorReport']}"
            raise Exception(f"Device driver error: '{msg}'")

        if 'Response' in response and response['Response'] is not None:
            msg = f"Got response: '{response['Response']}'"

        if 'Timing' in response and response['Timing'] is not None:
            request_duration = response['Timing']['Request']['Received'] - response['Timing']['Request']['Sent']
            response['Timing']['Response']['Received'] = datetime.datetime.now()
            response_duration: datetime.timedelta = response['Timing']['Response']['Received'] - response['Timing']['Response']['Sent']
            msg += f"request_duration: {request_duration}, response_duration: {response_duration}"
        
        if msg:
            self.logger.info(msg)

        return response

    def __del__(self):
        self.driver_process.kill()
        self.socket_to_driver.close()

class ReadyMode(Enum):
    Ready = 1
    Routed = 2
    NotAvailable = 3

class ReadyResponse:
    mode: ReadyMode
    message: str

def parse_ready_packet(packet: dict) -> bool:
    ret = ReadyResponse()
    ret.message = None

    if 'Response' not in packet:
        raise Exception("Missing 'Response' in packet")
    
    response = packet['Response']
    if 'Status' in response:
        if response['Status'] == 'ready':
            ret.mode = ReadyMode.Ready
        elif response['Status'] == 'routed':
            ret.mode = ReadyMode.Routed
            ret.message = f"Redirected to '{response["Redirect"]}'"
        elif response['Status'] == 'not-available':
            ret.mode = ReadyMode.NotAvailable
        else:
            raise Exception(f"Unknown Status='{response["Status"]}' from the driver")
    else:
        raise Exception(f"ready packet missing 'Status' key in 'Response'")
    
    return ret

if __name__ == '__main__':
    lipper = Lipper(equipment=Equipment.Test, equipment_id=3)

    ready_packet = lipper.receive()
    ready_packet = parse_ready_packet(ready_packet)
    lipper.logger.info(f"received ready packet with mode={ready_packet.mode}")

    if ready_packet.mode == ReadyMode.Ready or ready_packet.mode == ReadyMode.Routed:
        lipper.call(method='status')
        lipper.call(method='slewToCoordinates', ra=1.2, dec=3.4)
        lipper.call(method='move', position=10234)

    pass
