from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from utils import LAST_API_ROOT, init_log
import socket
import logging
import httpx
from enum import Enum
import asyncio
import xmltodict

default_sockets = {
    "Unknown1": False,
    "Unknown2": False,
    "Unknown3": False,
    "Unknown4": False,
    "Unknown5": False,
    "Unknown6": False,
}

logger = logging.getLogger('pswitch-driver')
init_log(logger)


router = APIRouter()
hostname = socket.gethostname()
hostname = hostname[:-1]
hostname = hostname.replace('last', 'pswitch')

class PswitchDriver():
    hostname: str
    ipaddr: str
    base_url: str
    _auth = ("admin", "admin")
    sockets: dict

    def __init__(self, side: str) -> None:
        # self.hostname = f"{hostname}{side}"
        self.hostname = f"pswitch02{side}"
        try:
            self.ipaddr = socket.gethostbyname(self.hostname)
        except Exception as ex:
             logger.exception(f"cannot get ipaddr for hostname={self.hostname}", exc_info=ex)
             return
        
        self.base_url = f"http://{self.ipaddr}"        
        self.refresh()


    async def getAsync(self, page: str = "/") -> str:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/{page}", auth=self._auth, timeout=5)
            if response.is_success:
                return response.content
            else:
                pass

    def get(self, page: str = "/") -> str:
        with httpx.Client() as client:
            response = client.get(f"{self.base_url}/{page}", auth=self._auth, timeout=5)
            if response.is_success:
                return response.content
            else:
                pass


    async def refreshAsync(self):
        try:
            dynamic_xml = await self.getAsync(page='st0.xml')
        except Exception as ex:
            logger.exception('HTTP Error', exc_info=ex)
            self.sockets = default_sockets
            self.temp = float('nan')
            return        
        static_xml = await self.getAsync(page='st2.xml')
        self.parse(dynamic_xml=dynamic_xml, static_xml=static_xml)


    def refresh(self):
        try:
            dynamic_xml = self.get(page='st0.xml')
        except Exception as ex:
            logger.exception('HTTP Error', exc_info=ex)
            self.sockets = default_sockets
            self.temp = float('nan')
            return        
        static_xml = self.get(page='st2.xml')
        self.parse(dynamic_xml=dynamic_xml, static_xml=static_xml)


    def parse(self, dynamic_xml: str, static_xml: str):
        self.sockets = dict()
        d = xmltodict.parse(dynamic_xml)
        dynamic_dict = d['response']
        d = xmltodict.parse(static_xml)
        static_dict = d['response']

        for i in range(0, 6):
            name = static_dict[f"r{i+6}"]
            state = True if dynamic_dict[f"out{i}"] == "1" else False
            self.sockets[name] = state        
        self.temp = float(dynamic_dict["ia1"]) / 10


    async def get_names(self) -> list:
        await self.refreshAsync()
        return [str(k) for k in self.sockets.keys()]
    
    @property
    async def names(self) -> list:
        names = await self.get_names()
        return names
    
    async def turnOn(self, socket_name: str) -> str:
        names = list(self.sockets.keys())
        if socket_name not in names:
            raise Exception(f"Bad socket name '{socket_name}'")
        idx = names.index(socket_name)
        await self.getAsync(page=f"/outs.cgi?out{idx}=1")
        return "ok"
    
    async def turnOff(self, socket_name: str) -> str:
        names = list(self.sockets.keys())
        if socket_name not in names:
            raise Exception(f"Bad socket name '{socket_name}'")
        idx = names.index(socket_name)
        await self.getAsync(page=f"/outs.cgi?out{idx}=0")
        return "ok"
    
    async def toggle(self, socket_name: str) -> str:
        names = list(self.sockets.keys())
        if socket_name not in names:
            raise Exception(f"Bad socket name '{socket_name}'")
        idx = names.index(socket_name)
        await self.getAsync(page=f"/outs.cgi?out={idx}")
        return "ok"
    
    async def temp(self) -> float:
        await self.refreshAsync()
        return self.temp


pswitch = {
    "e": PswitchDriver("e"),
    "w": PswitchDriver("w",)
}


class ValidSides(str, Enum):
    east = "e",
    west = "w",

#
# The functions below come in (east|west)_xxx pairs.  It looks like repetitive code but
#  since they are used by the openapi to extract number of parameters and their types
#  we need one for east and one for west.  It would've been nicer with a @decorator
#  but it would have needed an additional parameter, thus defeating the use for openapi :-(
#

# names
async def east_names() -> str: 
    names =  await pswitch["e"].names      
    return JSONResponse(names)
     
     
async def west_names() -> str:     
    names = await pswitch["w"].names      
    return JSONResponse(names)

        
# isOn
async def east_isOn(socket_name: str = Query(enum=list(pswitch["e"].sockets.keys()))) -> str:
    ps = pswitch["e"]
    await asyncio.sleep(0)
    if socket_name in list(ps.sockets.keys()):
        return JSONResponse(ps.sockets[socket_name])

        
async def west_isOn(socket_name: str = Query(enum=list(pswitch["w"].sockets.keys()))) -> str:
    ps = pswitch["w"]
    await asyncio.sleep(0)
    if socket_name in list(ps.sockets.keys()):
        return JSONResponse(ps.sockets[socket_name])


# turnOn
async def east_turnOn(socket_name: str = Query(enum=list(pswitch["e"].sockets.keys()))) -> str:
    await asyncio.sleep(0)
    return JSONResponse(pswitch["e"].turnOn(socket_name))

        
async def west_turnOn(socket_name: str = Query(enum=list(pswitch["w"].sockets.keys()))) -> str:
    await asyncio.sleep(0)
    return JSONResponse(pswitch["w"].turnOn(socket_name))

# turnOff
async def east_turnOff(socket_name: str = Query(enum=list(pswitch["e"].sockets.keys()))) -> str:
    await asyncio.sleep(0)
    return JSONResponse(pswitch["e"].turnOff(socket_name))

        
async def west_turnOff(socket_name: str = Query(enum=list(pswitch["w"].sockets.keys()))) -> str:
    await asyncio.sleep(0)
    return JSONResponse(pswitch["w"].turnOff(socket_name))

# toggle
async def east_toggle(socket_name: str = Query(enum=list(pswitch["e"].sockets.keys()))) -> str:
    await asyncio.sleep(0)
    return JSONResponse(pswitch["e"].toggle(socket_name))

        
async def west_toggle(socket_name: str = Query(enum=list(pswitch["w"].sockets.keys()))) -> str:
    await asyncio.sleep(0)
    return JSONResponse(pswitch["w"].toggle(socket_name))

# temp
async def east_temp() -> str:
    await asyncio.sleep(0)
    return JSONResponse(pswitch["e"].temp())

        
async def west_temp() -> str:
    await asyncio.sleep(0)
    return JSONResponse(pswitch["w"].temp())


for side in pswitch.keys():
    base_url = LAST_API_ROOT + f"{pswitch[side].hostname}"
    tag = pswitch[side].hostname

    router.add_api_route(path=base_url + "/names",   tags = [tag], endpoint=east_names    if side == "e" else west_names)
    router.add_api_route(path=base_url + "/isOn",    tags = [tag], endpoint=east_isOn     if side == "e" else west_isOn)
    router.add_api_route(path=base_url + "/turnOn",  tags = [tag], endpoint=east_turnOn   if side == "e" else west_turnOn)
    router.add_api_route(path=base_url + "/turnOff", tags = [tag], endpoint=east_turnOff  if side == "e" else west_turnOff)
    router.add_api_route(path=base_url + "/toggle",  tags = [tag], endpoint=east_toggle   if side == "e" else west_toggle)
    router.add_api_route(path=base_url + "/temp",    tags = [tag], endpoint=east_temp     if side == "e" else west_temp)
