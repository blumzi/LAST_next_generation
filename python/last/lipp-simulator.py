import datetime

from utils import Equipment, equipment_ids, init_log, DateTimeEncoder, datetime_decoder
import socket
from collections import OrderedDict
import json
import logging
import os
from lipp import LIPPRequest, LIPPResponse, LIPPReady, Timing
import argparse

class LIPPSimulator:
    unit_socket: socket.socket

    def __init__(self, socket_path: str) -> None:
        logger_name = f'{socket_path}-driver'
        self.logger = logging.getLogger(logger_name)
        init_log(self.logger)

        self.socket_path = f'\0{socket_path}'
        self.unit_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)

        ready = LIPPResponse()
        ready.RequestId = -1
        ready.Response = {'Status': 'ready'}
        ready.Error = None
        ready.ErrorReport = None
        ready.Timing = None
        
        self.send(ready)

    def receive(self) -> LIPPRequest:
        data, address = self.unit_socket.recvfrom(64*1024)
        self.logger.info(f"Received {len(data)} bytes '{data}' from {address}")
        self.peer_address = address
        request = LIPPRequest()
        d = json.loads(data.decode(), object_hook=datetime_decoder)
        request.RequestId = d['RequestId']
        request.Method = d['Method']
        for k, v in request.Parameters.items():
            request.Parameters[k] = v
        request.RequestTime = d['RequestTime']
        request.RequestReceived = datetime.datetime.now()

        return request
    
    def send(self, response):
        d = response if isinstance(response, dict) else response.__dict__
        data = json.dumps(d, cls=DateTimeEncoder).encode()
        self.logger.info(f"sending >>>'{data}'<<<")
        self.unit_socket.sendto(data, self.socket_path)



if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--socket', '-s', action='store', dest='socket')

    args = parser.parse_args()
    if args.socket is None:
        raise "Empty socket_path"
    
    simulator = LIPPSimulator(socket_path=args.socket)

    while True:
        request = simulator.receive()
        
        response = LIPPResponse()
        response.Timing.Request.Received = request.RequestReceived
        response.Timing.Request.Sent = request.RequestTime
        response.Response = f'dummy response to {request.Method}('
        for k, v in request.Parameters.items():
            response.Response += f'{k}={v}, '
        response.Response = response.Response.removesuffix(', ') + ')'
        response.Error = None
        response.ErrorReport = None
        response.Timing.Response.Sent = datetime.datetime.now()

        simulator.send(response.__dict__)
