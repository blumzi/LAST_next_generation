#
# This FastApi python source file was automatically generated:
#  - by the MATLAB code in 'obs.api.Wrapper.makeFastApiRoutes()'
#  - derived from the MATLAB class in '/home/ocs/matlab/LAST/LAST_CelestronFocusMotor/+inst/@CelestronFocuser/CelestronFocuser.m'
#  - for the 'focuser' type of LAST equipment
#  - on 01-Jan-2024 14:47:23
#
# Manual changes will be overridden!
#

from fastapi import APIRouter, Request
from utils import LAST_API_ROOT, PrettyJSONResponse, equipment_ids, Equipment, default_port, init_log
from validations import ValidEquipId
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
    focusers[id] = Forwarder(address=peer_hostname, port=default_port, equipment=Equipment.Focuser, equip_id=id)

# Method 'abort'
@router.get(LAST_API_ROOT + 'focuser/{id}/abort', tags=["focuser"], response_class=PrettyJSONResponse)
async def focuser_abort(id: ValidEquipId, request: Request):
    v = list()
    v.append(None)
    logger.info(f'focuser_abort: id={id} ')
    return await focusers[id].get(method='abort')

# Method 'test_exception'
@router.get(LAST_API_ROOT + 'focuser/{id}/test_exception', tags=["focuser"], response_class=PrettyJSONResponse)
async def focuser_test_exception(id: ValidEquipId, request: Request):
    v = list()
    v.append(None)
    logger.info(f'focuser_test_exception: id={id} ')
    return await focusers[id].get(method='test_exception')

# Method 'test_params'
@router.get(LAST_API_ROOT + 'focuser/{id}/test_params', tags=["focuser"], response_class=PrettyJSONResponse)
async def focuser_test_params(id: ValidEquipId, param1: str, param2: float, param3: bool, param4: int, request: Request):
    v = list()
    v.append(None)
    v.append(param1)
    v.append(param2)
    v.append(param3)
    v.append(param4)
    logger.info(f'focuser_test_params: id={id} param1={v[1]} param2={v[2]} param3={v[3]} param4={v[4]} ')
    return await focusers[id].get(method='test_params', param1=v[1], param2=v[2], param3=v[3], param4=v[4])

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
