
from fastapi import APIRouter, Request, Response, Path, Query
from fastapi.responses import JSONResponse
from utils import LAST_API_ROOT, PrettyJSONResponse, init_log
import socket
import logging
import httpx
from enum import Enum
from pydantic import BaseModel, Field
from threading import Thread
import json

import xmltodict
default_names = ["Unknown1", "Unknown2","Unknown3","Unknown4","Unknown5","Unknown6"]
pswitches = dict()

logger = logging.getLogger('pswitch-FastApi')
init_log(logger)


class SocketName(BaseModel):
    name: str = Field(..., description="Socket Name")
    description: str = Field(None, description="a b c")

tag = "pswitch01"

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
             logger.exception(f"cannot map hostname={self.hostname} to ipaddr", exc_info=ex)
             return
        
        self.base_url = f"http://{self.ipaddr}"

    async def get(self, page: str = "/") -> str:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/{page}", auth=self._auth, timeout=5)
            if response.is_success:
                return response.content
            else:
                pass

    async def refresh(self):
        try:
            xml = await self.get(page='st0.xml')
        except Exception as ex:
            logger.exception('HTTP Error', exc_info=ex)
            self.sockets = {
                "Unknown1": False,
                "Unknown2": False,
                "Unknown3": False,
                "Unknown4": False,
                "Unknown5": False,
                "Unknown6": False,
            }
            self.temp = float('nan')
            return

        d = xmltodict.parse(xml)
        dynamic_data = d['response']

        xml = await self.get(page='st2.xml')
        d = xmltodict.parse(xml)
        static_data = d['response']

        self.sockets = dict()
        for i in range(0, 6):
            name = static_data[f"r{i+6}"]
            state = True if dynamic_data[f"out{i}"] == "1" else False
            self.sockets[name] = state
        
        self.temp = float(dynamic_data["ia1"]) / 10

    async def get_names(self) -> list:
        await self.refresh()
        return [str(k) for k in self.sockets.keys()]
    
    @property
    async def names(self) -> list:
        names = await self.get_names()
        return names


pswitch = {
    "e": PswitchDriver("e"),
    "w": PswitchDriver("w",)
}

east_names = pswitch["e"].names
west_names = pswitch["w"].names

class ValidSides(str, Enum):
    east = "e",
    west = "w",

async def east_socket_names(): 
    names =  await pswitch["e"].names      
    return JSONResponse(names)
     
     
async def west_socket_names():     
    names = await pswitch["w"].names      
    return JSONResponse(names)

        
async def east_isOn(socket_name: str = Query(enum=east_names)) -> bool:
    ps = pswitch["e"]
    names = await ps.names
    if socket_name in names:
        state = ps.sockets[socket_name]
        return JSONResponse(state)

        
async def west_isOn(socket_name: str = Query(enum=west_names)) -> bool:
    ps = pswitch["w"]
    names = await ps.names
    if socket_name in names:
        state = ps.sockets[socket_name]
        return JSONResponse(state)
        
for side in pswitch.keys():
    base_url = LAST_API_ROOT + f"{pswitch[side].hostname}"
    tag = pswitch[side].hostname

    endpoint = east_socket_names if side == "e" else west_socket_names
    router.add_api_route(path=base_url + "/names", tags = [tag], endpoint=endpoint)

    # endpoint = east_isOn if side == "e" else west_isOn
    # router.add_api_route(path=base_url + "/isOn", tags = [tag], endpoint=endpoint)

# @router.get(LAST_API_ROOT + "pswitch/{side}/names", tags=[tag], response_class=PrettyJSONResponse)
# async def pswitch_names(side: ValidSides) -> list:
#     await pswitch[side].refresh()
#     return JSONResponse(pswitch[side].names())

    
# @router.get(LAST_API_ROOT + "pswitch/{side}/on", tags=[tag], response_class=PrettyJSONResponse)
# async def pswitch_on(side: ValidSides, socket_name: str):
#     await pswitch[side].refresh()
#     names = pswitch[side].names()
#     if socket_name not in names:
#         return JSONResponse({
#             'Error': f"Invalid socket name '{socket_name}'. Valid Names: {names}"
#         })
    
#     socket_number = names.index(socket_name)
#     pswitch[side].get(page=f"outs.cgi?out{socket_number}=1")
    
# @router.get(LAST_API_ROOT + "pswitch/{side}/off", tags=[tag], response_class=PrettyJSONResponse)
# async def pswitch_off(side: ValidSides, socket_name: str):
#     await pswitch[side].refresh()
#     names = pswitch[side].names()
#     if socket_name not in names:
#         return JSONResponse({
#             'Error': f"Invalid socket name '{socket_name}'. Valid Names: {names}"
#         })
    
#     socket_number = names.index(socket_name)
#     pswitch[side].get(page=f"outs.cgi?out{socket_number}=0")
    
# @router.get(LAST_API_ROOT + "pswitch/{side}/toggle", tags=[tag], response_class=PrettyJSONResponse)
# async def pswitch_toggle(side: ValidSides, socket_name: str):
#     await pswitch[side].refresh()
#     names = pswitch[side].names()
#     if socket_name not in names:
#         return JSONResponse({
#             'Error': f"Invalid socket name '{socket_name}'. Valid Names: {names}"
#         })
    
#     socket_number = names.index(socket_name)
#     pswitch[side].get(page=f"outs.cgi?out={socket_number}")

# @router.get(LAST_API_ROOT + "pswitch/{side}/isOn", tags=[tag], response_class=PrettyJSONResponse)
# async def pswitch_isOn(side: ValidSides, socket_name: str) -> bool:
#     await pswitch[side].refresh()
#     names = pswitch[side].names()
#     if socket_name not in names:
#         return JSONResponse({
#             'Error': f"Invalid socket name '{socket_name}'. Valid Names: {names}"
#         })
#     return JSONResponse(pswitch[side].sockets[socket_name])
    
# @router.get(LAST_API_ROOT + "pswitch/{side}/status", tags=[tag], response_class=PrettyJSONResponse)
# async def pswitch_status(side: ValidSides):
#     await pswitch[side].refresh()
#     return JSONResponse(pswitch[side].sockets)

    
# @router.get(LAST_API_ROOT + "pswitch/{side}/temp", tags=[tag], response_class=PrettyJSONResponse)
# async def pswitch_temp(side: ValidSides) -> float:
#     await pswitch[side].refresh()
#     return JSONResponse(pswitch[side].temp)