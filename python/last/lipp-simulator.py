import datetime

from utils import Equipment, equipment_ids, init_log, DateTimeEncoder, datetime_decoder
import socket
from collections import OrderedDict
import json
import logging
from lipp import Request, Response, Ready
import argparse
import sys

# import pydevd_pycharm
# pydevd_pycharm.settrace('localhost', stdoutToServer=True, stderrToServer=True)


class Simulator:
    socket: socket
    local_socket_path: str
    remote_socket_path: str

    def __init__(self, path: str) -> None:
        self.local_socket_path = f'\0{path}'
        self.remote_socket_path = f'\0{path.replace("driver", "unit")}'
        logger_name = self.local_socket_path[1:].replace('driver', 'drvr')
        self.logger = logging.getLogger(logger_name)
        init_log(self.logger)

        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.socket.bind(self.local_socket_path)

        ready = Response()
        ready.RequestId = -1
        ready.Response = {'Status': 'ready'}
        ready.Error = None
        ready.ErrorReport = None
        ready.Timing = None

        self.send(ready)

    def receive(self) -> Request:
        data, address = self.socket.recvfrom(64 * 1024)
        # self.logger.info(f"Received {len(data)} bytes '{data}' from {address}")
        incoming = Request()
        d = json.loads(data.decode(), object_hook=datetime_decoder)
        incoming.RequestId = d['RequestId']
        incoming.Method = d['Method']
        if incoming.Method == 'quit':
            self.logger.info("Exiting on 'quit' request")
            self.socket.close()
            sys.exit()
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
    parser.add_argument('--socket-path', '-s', action='store', dest='socket_path')

    args = parser.parse_args()
    if args.socket_path is None:
        raise Exception("Empty socket_path")

    logger = logging.getLogger('lipp-drvr-{args.socket_path}')
    init_log(logger)
    logger.debug(f"started with socket path '{args.socket_path}'")
    simulator = Simulator(path=args.socket_path)

    while True:
        request = simulator.receive()
        
        response = Response()
        response.Timing = {'Request': {}, 'Response': {}}

        response.RequestId = request.RequestId
        response.Timing['Request']['Received'] = request.RequestReceived
        response.Timing['Request']['Sent'] = request.RequestTime
        response.Response = f'dummy response to {request.Method}('
        if 'Parameters' in request.__dict__ and request.Parameters is not None and len(request.Parameters) > 0:
            for k, v in request.Parameters.items():
                response.Response += f'{k}={v}, '
            response.Response = response.Response[:-2] + ')'
        else:
            response.Response += ')'
        response.Error = None
        response.ErrorReport = None
        response.Timing['Response']['Sent'] = datetime.datetime.now()

        simulator.send(response)
