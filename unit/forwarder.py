import httpx
import asyncio
import socket
import traceback
import logging
from utils import Equipment, init_log, LAST_API_ROOT, ResponseDict
from urllib.parse import urlencode
import sys
from driver_interface import DriverInterface

class Forwarder(DriverInterface):
    remote_address: str = None
    port: str = "8000"
    base_url: str
    equip: Equipment
    equip_name: str
    equip_id: int
    _available: bool = False
    _reason: str = None

    def __init__(self, address: str, port: int = -1, equip: Equipment = Equipment.Undefined, equip_id: int = 0) -> None:
        if address:
            self.remote_address = address
        else:
            hostname = socket.gethostname()
            if hostname.startswith('last'):
                self.remote_address = hostname[1:-1] + 'w' if hostname[-1] == 'e' else 'e'
            else:
                raise Exception(f"don't know how to handle hostname='{hostname}'")
            
        if equip == Equipment.Undefined:
            raise Exception(f"must specify an equipment type different from 'Undefined'")
        else:
            self.equip = equip

        if (equip == Equipment.Camera or equip == Equipment.Focuser) and equip_id not in [1, 2, 3, 4]:
            raise Exception(f"Invalid equip_id '{equip_id}' for equip='{self.equip}', must be one of [1, 2, 3, 4]")
        
        if equip == Equipment.Pswitch and equip_id not in [1, 2]:
            raise Exception(f"Invalid equip_id '{equip_id}' for equip='{self.equip}', must be one of [1, 2]")
        
        self.equip_id = equip_id

        if port != -1:
            self.port = port
        
        self.equip_name = str(self.equip).replace('Equipment.', '').lower()
        self.base_url = f"http://{self.remote_address}:{self.port}{LAST_API_ROOT}{self.equip_name}/{self.equip_id}"

        self.logger = logging.getLogger(f"forwarder-{self.equip_name}-{equip_id}")
        init_log(self.logger)
        

    async def get(self, method, params) -> dict:
        url = self.base_url + '/' + method
        if params is not None:
            url += "?" + urlencode(params)
        self.logger.info(f"forwarding get(url='{url}')")
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, timeout=10)
                self._available = True
                self._reason = None
                return response
            except (httpx.ReadTimeout, httpx.ConnectTimeout, httpx.TimeoutException) as ex:
                self._available = False
                self._reason = "HTTP timeout after 10 seconds"
                self.logger.info(f"timeout")
                return {
                    'Response': None,
                    'Exception': f"{ex}"
                }
            except Exception as ex:
                self._available = False
                self._reason = f"{ex.message}"
                self.logger.info(f"Exception:{ex.message}")
                return {
                    'Response': None,
                    'Exception': f"{ex}",
                }
    

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
            
    def available(self) -> bool:
        return self._available
    
    def reason_for_not_available(self) -> str:
        return self._reason