import datetime

from utils import Equipment, equipment_ids, init_log
import socket
from collections import OrderedDict
import json
import logging
from subprocess import Popen


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
    Error: str
    ErrorReport: str
    Timing: Timing


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
        logger_name = f'lipper-{equipment}'
        if equipment_id is not None:
            logger_name += f'-{equipment_id}'
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

        self.socket_path = f'\0lipp-{equipment}'
        if equipment_id is not None:

            self.socket_path += f'-{equipment_id}'

        self.socket_to_driver = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.socket_to_driver.bind(self.socket_path)
        self.current_request_id = -1

        matlab_script = f'obs.ng.DeviceDriver("SocketPath", "{self.socket_path}", "Equipment", "{equipment}"'
        if equipment_id is not None:
            matlab_script += f', "EquipmentId", {equipment_id}'
        matlab_script += ');'

        self.driver_process = Popen(args=['matlab', '-nodisplay', '-batch', matlab_script],
                                    shell=True,
                                    cwd='/home/ocs/matlab')

    def call(self, method: str, **kwargs):
        request = LIPPRequest()
        self.current_request_id += 1
        request.RequestId = self.current_request_id
        request.Method = method
        for k, v in kwargs.items():
            request.Parameters[k] = v
        request.RequestTime = datetime.datetime.now()
        data = json.dumps(request).encode()
        self.logger.info("Sending '{data}' on '{self.socket_path[1:]}'")
        self.pending_request = request
        self.socket_to_driver.sendto(data, self.socket_path)

    def receive(self) -> object:
        data, address = self.socket_to_driver.recvfrom(self._max_bytes)
        response: LIPPResponse = json.loads(data.decode())

        if response.RequestId != self.current_request_id:
            pass  # TODO: what do we do

        if response.Error is not None:
            msg = response.Error
            if response.ErrorReport is not None:
                msg += f" - {response.ErrorReport}"
            raise f"Device driver error: '{msg}'"

        request_duration = response.Timing.Request.Received - response.Timing.Request.Sent
        response.Timing.Response.Received = datetime.datetime.now()
        response_duration: datetime.timedelta = response.Timing.Response.Received - response.Timing.Response.Sent
        self.logger.info(f"Got response: '{response.Response}', " +
                         f"request_duration: {request_duration}, response_duration: {response_duration}")
        return json.loads(response.Response)

    def __del__(self):
        self.driver_process.kill()
        self.socket_to_driver.close()


if __name__ == '__main__':
    lipper = Lipper(equipment=Equipment.Test, equipment_id=1)
