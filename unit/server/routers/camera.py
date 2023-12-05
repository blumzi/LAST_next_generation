#
# This FastApi python source file was automatically generated:
#  - by the MATLAB code in 'obs.api.Wrapper.makeFastApiRoutes()'
#  - derived from the MATLAB class in '/home/ocs/matlab/LAST/LAST_QHYccd/+inst/@QHYccd/QHYccd.m'
#  - for the 'camera' type of LAST equipment
#  - on 05-Dec-2023 14:12:55
#
# Manual changes will be overridden!
#

from fastapi import APIRouter, Request
from utils import LAST_API_ROOT, PrettyJSONResponse, equipment_ids, Equipment, default_port, init_log, ValidEquipId
import socket
from forwarder import Forwarder
import logging
import lipp
import threading

logger = logging.getLogger('camera-FastApi')
init_log(logger)

router = APIRouter()
hostname = socket.gethostname()
if hostname.startswith('last'):
    this_side = hostname[-1]
if this_side == 'w':
    peer_side = 'e'
else:
    peer_side = 'w'
peer_hostname = hostname[:-1] + peer_side


cameras = [None, None, None, None, None]
for id in equipment_ids[this_side]:
    lipp.Driver(cameras, Equipment.Camera, id)

for id in equipment_ids[peer_side]:
    cameras[id] = Forwarder(address=peer_hostname, port=default_port, equipment=Equipment.Camera, equip_id=id)

# Method 'abort'
@router.get(LAST_API_ROOT + 'camera/{id}/abort', tags=["camera"], response_class=PrettyJSONResponse)
async def camera_abort(id: ValidEquipId, request: Request):
    v = list()
    v.append(None)
    logger.info(f'camera_abort: id={id} ')
    return await cameras[id].get(method='abort')

# Method 'saveCurImage'
@router.get(LAST_API_ROOT + 'camera/{id}/saveCurImage', tags=["camera"], response_class=PrettyJSONResponse)
async def camera_saveCurImage(id: ValidEquipId, request: Request):
    v = list()
    v.append(None)
    logger.info(f'camera_saveCurImage: id={id} ')
    return await cameras[id].get(method='saveCurImage')

# Method 'takeExposure'
@router.get(LAST_API_ROOT + 'camera/{id}/takeExposure', tags=["camera"], response_class=PrettyJSONResponse)
async def camera_takeExposure(id: ValidEquipId, request: Request):
    v = list()
    v.append(None)
    logger.info(f'camera_takeExposure: id={id} ')
    return await cameras[id].get(method='takeExposure')

# Method 'takeLive'
@router.get(LAST_API_ROOT + 'camera/{id}/takeLive', tags=["camera"], response_class=PrettyJSONResponse)
async def camera_takeLive(id: ValidEquipId, num: float, request: Request):
    v = list()
    v.append(None)
    v.append(num)
    logger.info(f'camera_takeLive: id={id} num={v[1]} ')
    return await cameras[id].get(method='takeLive', num=v[1])

# Property 'CamStatus' getter
@router.get(LAST_API_ROOT + 'camera/{id}/CamStatus', tags=["camera"], response_class=PrettyJSONResponse)
async def camera_CamStatus_get(id: ValidEquipId, request: Request) -> float:
    logger.info(f'camera_CamStatus_get: id={id}')
    return await cameras[id].get(method='CamStatus')

# Property 'Connected' getter
@router.get(LAST_API_ROOT + 'camera/{id}/Connected', tags=["camera"], response_class=PrettyJSONResponse)
async def camera_Connected_get(id: ValidEquipId, request: Request) -> float:
    logger.info(f'camera_Connected_get: id={id}')
    return await cameras[id].get(method='Connected')

# Property 'ExpTime' getter
@router.get(LAST_API_ROOT + 'camera/{id}/ExpTime', tags=["camera"], response_class=PrettyJSONResponse)
async def camera_ExpTime_get(id: ValidEquipId, request: Request) -> float:
    logger.info(f'camera_ExpTime_get: id={id}')
    return await cameras[id].get(method='ExpTime')

# Property 'Gain' getter
@router.get(LAST_API_ROOT + 'camera/{id}/Gain', tags=["camera"], response_class=PrettyJSONResponse)
async def camera_Gain_get(id: ValidEquipId, request: Request) -> float:
    logger.info(f'camera_Gain_get: id={id}')
    return await cameras[id].get(method='Gain')

# Property 'Offset' getter
@router.get(LAST_API_ROOT + 'camera/{id}/Offset', tags=["camera"], response_class=PrettyJSONResponse)
async def camera_Offset_get(id: ValidEquipId, request: Request) -> float:
    logger.info(f'camera_Offset_get: id={id}')
    return await cameras[id].get(method='Offset')

# Property 'ReadMode' getter
@router.get(LAST_API_ROOT + 'camera/{id}/ReadMode', tags=["camera"], response_class=PrettyJSONResponse)
async def camera_ReadMode_get(id: ValidEquipId, request: Request) -> float:
    logger.info(f'camera_ReadMode_get: id={id}')
    return await cameras[id].get(method='ReadMode')

# Property 'Temperature' getter
@router.get(LAST_API_ROOT + 'camera/{id}/Temperature', tags=["camera"], response_class=PrettyJSONResponse)
async def camera_Temperature_get(id: ValidEquipId, request: Request) -> float:
    logger.info(f'camera_Temperature_get: id={id}')
    return await cameras[id].get(method='Temperature')

# Property 'UnitHeaderCell' getter
@router.get(LAST_API_ROOT + 'camera/{id}/UnitHeaderCell', tags=["camera"], response_class=PrettyJSONResponse)
async def camera_UnitHeaderCell_get(id: ValidEquipId, request: Request) -> float:
    logger.info(f'camera_UnitHeaderCell_get: id={id}')
    return await cameras[id].get(method='UnitHeaderCell')
