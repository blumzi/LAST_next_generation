#
# This FastApi python source file was automatically generated:
#  - by the MATLAB code in 'obs.api.Wrapper.makeFastApiRoutes()'
#  - derived from the MATLAB class in '/home/ocs/matlab/LAST/LAST_CelestronFocusMotor/+inst/@CelestronFocuser/CelestronFocuser.m'
#  - for the 'focuser' type of LAST equipment
#  - on 23-Nov-2023 16:43:27
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

logger = logging.getLogger('focuser-FastApi')
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


focusers = [None, None, None, None, None]
for id in equipment_ids[this_side]:
    lipp.Driver(focusers, Equipment.Focuser, id)

for id in equipment_ids[peer_side]:
    focusers[id] = Forwarder(address=peer_hostname, port=default_port, equip=Equipment.Focuser, equip_id=id)

# Method 'abort'
@router.get(LAST_API_ROOT + 'focuser/{id}/abort', tags=["focuser"], response_class=PrettyJSONResponse)
async def focuser_abort(id: ValidEquipId, request: Request):
    logger.info(f'focuser_abort: id={id} ')
    return await focusers[id].get(method='abort')

# Method 'explode'
@router.get(LAST_API_ROOT + 'focuser/{id}/explode', tags=["focuser"], response_class=PrettyJSONResponse)
async def focuser_explode(id: ValidEquipId, param1: str, param2: float, request: Request):
    logger.info(f'focuser_explode: id={id} param1={param1} param2={param2} ')
    return await focusers[id].get(method='explode', param1=str, param2=float)

# Property 'Connected' getter
@router.get(LAST_API_ROOT + 'focuser/{id}/Connected', tags=["focuser"], response_class=PrettyJSONResponse)
async def focuser_Connected_get(id: ValidEquipId, request: Request) -> bool:
    logger.info(f'focuser_Connected_get: id={id}')
    return await focusers[id].get(method='Connected')

# Property 'Connected' setter
@router.put(LAST_API_ROOT + 'focuser/{id}/Connected', tags=["focuser"], response_class=PrettyJSONResponse)
async def focuser_Connected_set(id: ValidEquipId, value: bool, request: Request):
    logger.info(f'focuser_Connected_set: id={id} value={value}')
    return await focusers[id].put(method='Connected', value=value)

# Property 'Limits' getter
@router.get(LAST_API_ROOT + 'focuser/{id}/Limits', tags=["focuser"], response_class=PrettyJSONResponse)
async def focuser_Limits_get(id: ValidEquipId, request: Request) -> float:
    logger.info(f'focuser_Limits_get: id={id}')
    return await focusers[id].get(method='Limits')

# Property 'Pos' getter
@router.get(LAST_API_ROOT + 'focuser/{id}/Pos', tags=["focuser"], response_class=PrettyJSONResponse)
async def focuser_Pos_get(id: ValidEquipId, request: Request) -> float:
    logger.info(f'focuser_Pos_get: id={id}')
    return await focusers[id].get(method='Pos')

# Property 'Status' getter
@router.get(LAST_API_ROOT + 'focuser/{id}/Status', tags=["focuser"], response_class=PrettyJSONResponse)
async def focuser_Status_get(id: ValidEquipId, request: Request) -> str:
    logger.info(f'focuser_Status_get: id={id}')
    return await focusers[id].get(method='Status')
