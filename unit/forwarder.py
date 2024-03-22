import httpx
import socket
import logging
from utils import Equipment, init_log, LAST_API_ROOT, TriState
from urllib.parse import urlencode
from driver_interface import DriverInterface
import datetime
import json


class Forwarder(DriverInterface):
    remote_address: str = None
    port: int = 8000
    base_url: str
    equipment: Equipment
    equip: str
    equip_id: int
    _reason: str = None
    _info: dict
    _responding: TriState = None

    def __init__(self, address: str, port: int = -1, equipment: Equipment = Equipment.Undefined, equip_id: int = 0):
        DriverInterface.__init__(self, equipment_type=equipment, equipment_id=equip_id)
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

        self._responding = False
        self._last_response = datetime.datetime.min

        self.logger = logging.getLogger(f"forwarder-{equip_name}-{self.equip_id}")
        init_log(self.logger)
        self.logger.info(f"Started forwarding to {self.base_url}")

    async def get(self, method: str, **kwargs) -> dict:
        url = self.base_url + '/' + method
        if kwargs != {}:
            url += "?" + urlencode(kwargs)
        self.logger.info(f"forwarding get(url='{url}')")
        
        async with httpx.AsyncClient(trust_env=False) as client:  # must have trust_env=False, to ignore proxy
            timeout = 5
            try:
                response = await client.get(url, timeout=timeout, follow_redirects=False)
                response.raise_for_status()
                self._responding = True
                self._last_response = datetime.datetime.now()
                self._detected = True  # there was no exception -> we are detected
            except Exception as ex:
                self._detected = False
                self._responding = False
                self.logger.error(f"HTTP error ({ex.args[0]})")
                return {
                    'Error': ex.args[0]
                }
            
            if response.is_success:
                data = json.loads(response.content)
                return data

    async def put(self, method: str, **kwargs) -> dict:
        url = self.base_url + '/' + method
        if kwargs != {}:
            url += "?" + urlencode(kwargs)
        self.logger.info(f"forwarding get(url='{url}')")
        async with httpx.AsyncClient(trust_env=False) as client:  # must have trust_env=False, to ignore proxy
            timeout = 5
            try:
                response = await client.put(url, timeout=timeout, follow_redirects=False)
                response.raise_for_status()
                self._detected = True
            except Exception as ex:
                self._detected = False
                self.logger.error(f"HTTP error ({ex.args[0]})")
                return {'Error': ex.args[0]}
            
            if response.is_success:
                data = json.loads(response.content)
                return data

    def info(self):
        return self._info
    
    def status(self):
        return {
            'responding': self._responding,
            'last_response': self._last_response,
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
    def last_response(self) -> datetime.datetime:
        return self._last_response
