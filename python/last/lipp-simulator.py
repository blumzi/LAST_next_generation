import datetime

from utils import Equipment, equipment_ids, init_log, DateTimeEncoder, datetime_decoder
import socket
from collections import OrderedDict
import json
import logging
import os
from lipp import LIPPRequest, LIPPResponse, LIPPReady
import argparse

# import pydevd_pycharm
# pydevd_pycharm.settrace('localhost', stdoutToServer=True, stderrToServer=True)


class LIPPSimulator:
    socket: socket.socket
    local_socket_path: str
    remote_socket_path: str

    def __init__(self, path: str) -> None:
        self.remote_socket_path = f'\0{path}'
        self.local_socket_path = self.remote_socket_path.replace('unit', 'driver')
        logger_name = self.local_socket_path[1:]
        self.logger = logging.getLogger(logger_name)
        init_log(self.logger)

        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.socket.bind(self.local_socket_path)

        ready = LIPPResponse()
        ready.RequestId = -1
        ready.Response = {'Status': 'ready'}
        ready.Error = None
        ready.ErrorReport = None
        ready.Timing = None

        self.send(ready)

    def receive(self) -> LIPPRequest:
        data, address = self.socket.recvfrom(64 * 1024)
        # self.logger.info(f"Received {len(data)} bytes '{data}' from {address}")
        incoming = LIPPRequest()
        d = json.loads(data.decode(), object_hook=datetime_decoder)
        incoming.RequestId = d['RequestId']
        incoming.Method = d['Method']
        incoming.Parameters = {}
        if 'Parameters' in d and d['Parameters'] is not None:
            for key, value in d['Parameters'].items():
                incoming.Parameters[key] = value
        incoming.RequestTime = d['RequestTime']
        incoming.RequestReceived = datetime.datetime.now()

        return incoming
    
    def send(self, outgoing):
        d = outgoing if isinstance(outgoing, dict) else outgoing.__dict__
        data = json.dumps(d, cls=DateTimeEncoder).encode()
        #self.logger.info(f"sending >>>'{data}' on '{self.remote_socket_path}' <<<")
        self.socket.sendto(data, self.remote_socket_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--unit-socket', '-s', action='store', dest='socket')

    args = parser.parse_args()
    if args.socket is None:
        raise Exception("Empty socket_path")

    logger = logging.getLogger('lipp-simulator')
    init_log(logger)
    logger.debug(f"started with socket path '{args.socket}'")
    simulator = LIPPSimulator(path=args.socket)

    while True:
        request = simulator.receive()
        
        response = LIPPResponse()
        response.Timing = {'Request': {}, 'Response': {}}

        response.RequestId = request.RequestId
        response.Timing['Request']['Received'] = request.RequestReceived
        response.Timing['Request']['Sent'] = request.RequestTime
        response.Response = f'dummy response to {request.Method}('
        if 'Parameters' in request.__dict__:
            for k, v in request.Parameters.items():
                response.Response += f'{k}={v}, '
        response.Response = response.Response.removesuffix(', ') + ')'
        response.Error = None
        response.ErrorReport = None
        response.Timing['Response']['Sent'] = datetime.datetime.now()

        simulator.send(response)
