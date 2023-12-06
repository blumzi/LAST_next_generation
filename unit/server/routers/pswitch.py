
from fastapi import APIRouter, Request, Response, Path, Query
from fastapi.responses import JSONResponse
from utils import LAST_API_ROOT, PrettyJSONResponse, init_log
import socket
import logging
import httpx
from enum import Enum
from pydantic import BaseModel, Field
from threading import Thread
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

logger = logging.getLogger('pswitch-FastApi')
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
             logger.exception(f"cannot map hostname={self.hostname} to ipaddr", exc_info=ex)
             return
        
        self.base_url = f"http://{self.ipaddr}"
        
        for side in ["e", "w"]:
            try:
                for page in ["st0.xml", "st2.xml"]:
                    with httpx.Client() as client:
                        response = client.get(f"{self.base_url}/{page}", auth=self._auth, timeout=5)
                        response.raise_for_status()
                        if response.is_success:
                            if page == "st0.xml":
                                dynamic_data = xmltodict.parse(response.content)
                                values = list()
                                for i in range(1, 7):
                                    values.append(dynamic_data['response'][f"out{i}"])
                            else:                         
                                static_data = xmltodict.parse(response.content)
                                names = list()
                                for i in range(6, 12):
                                    names.append(static_data['response'][f"r{i}"])
                        else:
                            self.sockets = default_sockets
            except Exception as ex:
                self.sockets = default_sockets
            
            self.sockets = dict()
            for i in range(0, 6):
                self.sockets[names[i]] = True if values[i] == '1' else False

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
    
    async def turnOn(self, socket_name: str) -> str:
        names = list(self.sockets.keys())
        if socket_name not in names:
            raise Exception(f"Bad socket name '{socket_name}'")
        idx = names.index(socket_name)
        await self.get(page=f"/outs.cgi?out{idx}=1")
        return "ok"
    
    async def turnOff(self, socket_name: str) -> str:
        names = list(self.sockets.keys())
        if socket_name not in names:
            raise Exception(f"Bad socket name '{socket_name}'")
        idx = names.index(socket_name)
        await self.get(page=f"/outs.cgi?out{idx}=0")
        return "ok"
    
    async def toggle(self, socket_name: str) -> str:
        names = list(self.sockets.keys())
        if socket_name not in names:
            raise Exception(f"Bad socket name '{socket_name}'")
        idx = names.index(socket_name)
        await self.get(page=f"/outs.cgi?out={idx}")
        return "ok"


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

        
# isOn
async def east_isOn(socket_name: str = Query(enum=list(pswitch["e"].sockets.keys()))) -> bool:
    ps = pswitch["e"]
    await asyncio.sleep(0)
    if socket_name in list(ps.sockets.keys()):
        return JSONResponse(ps.sockets[socket_name])

        
async def west_isOn(socket_name: str = Query(enum=list(pswitch["w"].sockets.keys()))) -> bool:
    ps = pswitch["w"]
    await asyncio.sleep(0)
    if socket_name in list(ps.sockets.keys()):
        return JSONResponse(ps.sockets[socket_name])


# turnOn
async def east_turnOn(socket_name: str = Query(enum=list(pswitch["e"].sockets.keys()))) -> bool:
    await asyncio.sleep(0)
    return JSONResponse(pswitch["e"].turnOn(socket_name))

        
async def west_turnOn(socket_name: str = Query(enum=list(pswitch["w"].sockets.keys()))) -> bool:
    await asyncio.sleep(0)
    return JSONResponse(pswitch["w"].turnOn(socket_name))

# turnOff
async def east_turnOff(socket_name: str = Query(enum=list(pswitch["e"].sockets.keys()))) -> bool:
    await asyncio.sleep(0)
    return JSONResponse(pswitch["e"].turnOff(socket_name))

        
async def west_turnOff(socket_name: str = Query(enum=list(pswitch["w"].sockets.keys()))) -> bool:
    await asyncio.sleep(0)
    return JSONResponse(pswitch["w"].turnOff(socket_name))

# toggle
async def east_toggle(socket_name: str = Query(enum=list(pswitch["e"].sockets.keys()))) -> bool:
    await asyncio.sleep(0)
    return JSONResponse(pswitch["e"].toggle(socket_name))

        
async def west_toggle(socket_name: str = Query(enum=list(pswitch["w"].sockets.keys()))) -> bool:
    await asyncio.sleep(0)
    return JSONResponse(pswitch["w"].toggle(socket_name))


for side in pswitch.keys():
    base_url = LAST_API_ROOT + f"{pswitch[side].hostname}"
    tag = pswitch[side].hostname

    router.add_api_route(path=base_url + "/names",   tags = [tag], endpoint=east_socket_names if side == "e" else west_socket_names)
    router.add_api_route(path=base_url + "/isOn",    tags = [tag], endpoint=east_isOn         if side == "e" else west_isOn)
    router.add_api_route(path=base_url + "/turnOn",  tags = [tag], endpoint=east_turnOn       if side == "e" else west_turnOn)
    router.add_api_route(path=base_url + "/turnOff", tags = [tag], endpoint=east_turnOff      if side == "e" else west_turnOff)
    router.add_api_route(path=base_url + "/toggle",  tags = [tag], endpoint=east_toggle       if side == "e" else west_toggle)

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