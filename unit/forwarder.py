import httpx
import socket
import traceback
import logging
from utils import Equipment, init_log, LAST_API_ROOT, DriverState
from urllib.parse import urlencode
import sys
from driver_interface import DriverInterface
from fastapi.responses import JSONResponse

class Forwarder(DriverInterface):
    remote_address: str = None
    port: str = "8000"
    base_url: str
    equipment: Equipment
    equip: str
    equip_id: int
    _reason: str = None
    _state = DriverState.Unknown
    _info: dict

    def __init__(self, address: str, port: int = -1, equipment: Equipment = Equipment.Undefined, equip_id: int = 0) -> None:
        if address:
            self.remote_address = address
        else:
            hostname = socket.gethostname()
            if hostname.startswith('last'):
                self.remote_address = hostname[1:-1] + 'w' if hostname[-1] == 'e' else 'e'
            else:
                raise Exception(f"don't know how to handle hostname='{hostname}'")
            
        if equipment == Equipment.Undefined:
            raise Exception(f"must specify an equipment type different from 'Undefined'")
        else:
            self.equipment = equipment

        if (equipment == Equipment.Camera or equipment == Equipment.Focuser) and equip_id not in [1, 2, 3, 4]:
            raise Exception(f"Invalid equip_id '{equip_id}' for equip='{self.equipment}', must be one of [1, 2, 3, 4]")
        
        self.equip_id = equip_id

        if port != -1:
            self.port = port
        
        self.equip = f"{self.equipment}-{self.equip_id}"
        
        equip_name = str(self.equipment).replace('Equipment.', '').lower()
        self.base_url = f"http://{self.remote_address}:{self.port}{LAST_API_ROOT}{equip_name}/{self.equip_id}"

        self._info = {
            'Type': 'HTTP Forwarder',
            'Equipment': f"{equip_name}-{self.equip_id}",
            'Url': self.base_url,
        }

        self._state = DriverState.Available

        self.logger = logging.getLogger(f"forwarder-{equip_name}-{self.equip_id}")
        init_log(self.logger)
        self.logger.info(f"Started forwarding to {self.base_url}")
        

    async def get(self, method: str, **kwargs) -> dict:
        url = self.base_url + '/' + method
        if kwargs != {}:
            url += "?" + urlencode(kwargs)
        self.logger.info(f"forwarding get(url='{url}')")
        
        async with httpx.AsyncClient() as client:
            timeout = 5
            try:
                response = await client.get(url, timeout=timeout, follow_redirects=False)
                response.raise_for_status()
            except Exception as ex:
                self._state = DriverState.Unavailable
                self.logger.error(f"HTTP error ({ex.args[0]})")
                return JSONResponse({
                    'Error': ex.args[0]
                })
            
            if response.is_success:
                self._state = DriverState.Available
                return response.content
    

    async def put(self, method, params) -> dict:
        async with httpx.AsyncClient() as client:
            try:
                url = self.base_url + '/' + method
                if params is not None:
                    url += "?" + urlencode(params)
                self.logger.info(f"forwarding get(url='{url}')")
                return {
                    'Response': f"dummy response for url='{url}'",
                    # 'Response': await client.put(url),
                    'Error': None,
                    'ErrorReport': None,
                }
            except Exception as ex:
                return {
                    'Response': None,
                    'Error': 'f{ex}',
                    'ErrorReport': traceback.format_exception(sys.exc_info()),
                }
            
    def info(self):
        return self._info
    
    def status(self):
        pass

    def state(self) -> DriverState:
        return self._state