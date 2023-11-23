#
# This FastApi python source file was automatically generated:
#  - by the MATLAB code in 'obs.api.Wrapper.makeFastApiRoutes()'
#  - derived from the MATLAB class in '/home/ocs/matlab/LAST/LAST_XerxesMount/+inst/@XerxesMountBinary/XerxesMountBinary.m'
#  - for the 'mount' type of LAST equipment
#  - on 23-Nov-2023 16:43:28
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

logger = logging.getLogger('mount-FastApi')
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


mounts = [None]
lipp.Driver(mounts, Equipment.Mount)

# Method 'abort'
@router.get(LAST_API_ROOT + 'mount/abort', tags=["mount"], response_class=PrettyJSONResponse)
async def mount_abort(request: Request):
    logger.info(f'mount_abort:')
    return await mounts[0].get(method='abort')

# Method 'goTo'
@router.get(LAST_API_ROOT + 'mount/goTo', tags=["mount"], response_class=PrettyJSONResponse)
async def mount_goTo(a1: float, a2: float, coordtype: float, request: Request):
    logger.info(f'mount_goTo:a1={a1} a2={a2} coordtype={coordtype} ')
    return await mounts[0].get(method='goTo', a1=float, a2=float, coordtype=float)

# Method 'park'
@router.get(LAST_API_ROOT + 'mount/park', tags=["mount"], response_class=PrettyJSONResponse)
async def mount_park(request: Request):
    logger.info(f'mount_park:')
    return await mounts[0].get(method='park')

# Method 'reset'
@router.get(LAST_API_ROOT + 'mount/reset', tags=["mount"], response_class=PrettyJSONResponse)
async def mount_reset(request: Request):
    logger.info(f'mount_reset:')
    return await mounts[0].get(method='reset')

# Property 'Alt' getter
@router.get(LAST_API_ROOT + 'mount/Alt', tags=["mount"], response_class=PrettyJSONResponse)
async def mount_Alt_get(request: Request) -> float:
    logger.info(f'mount_Alt_get')
    return await mounts[0].get(method='Alt')

# Property 'Az' getter
@router.get(LAST_API_ROOT + 'mount/Az', tags=["mount"], response_class=PrettyJSONResponse)
async def mount_Az_get(request: Request) -> float:
    logger.info(f'mount_Az_get')
    return await mounts[0].get(method='Az')

# Property 'Connected' getter
@router.get(LAST_API_ROOT + 'mount/Connected', tags=["mount"], response_class=PrettyJSONResponse)
async def mount_Connected_get(request: Request) -> float:
    logger.info(f'mount_Connected_get')
    return await mounts[0].get(method='Connected')

# Property 'Dec' getter
@router.get(LAST_API_ROOT + 'mount/Dec', tags=["mount"], response_class=PrettyJSONResponse)
async def mount_Dec_get(request: Request) -> float:
    logger.info(f'mount_Dec_get')
    return await mounts[0].get(method='Dec')

# Property 'HA' getter
@router.get(LAST_API_ROOT + 'mount/HA', tags=["mount"], response_class=PrettyJSONResponse)
async def mount_HA_get(request: Request) -> float:
    logger.info(f'mount_HA_get')
    return await mounts[0].get(method='HA')

# Property 'RA' getter
@router.get(LAST_API_ROOT + 'mount/RA', tags=["mount"], response_class=PrettyJSONResponse)
async def mount_RA_get(request: Request) -> float:
    logger.info(f'mount_RA_get')
    return await mounts[0].get(method='RA')

# Property 'Status' getter
@router.get(LAST_API_ROOT + 'mount/Status', tags=["mount"], response_class=PrettyJSONResponse)
async def mount_Status_get(request: Request) -> float:
    logger.info(f'mount_Status_get')
    return await mounts[0].get(method='Status')
