from fastapi import APIRouter, Request
from utils import LAST_API_ROOT, PrettyJSONResponse, equipment_ids, Equipment, default_port, init_log, ValidEquipId, ResponseDict
import socket
from forwarder import Forwarder
import logging
import lipp

logger = logging.getLogger('unit-FastApi')
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

from server.routers.camera import cameras
from server.routers.focuser import focusers
from server.routers.mount import mounts


# Method 'abort'
@router.get(LAST_API_ROOT + 'unit/status', tags=["unit"], response_class=PrettyJSONResponse)
async def mount_abort(request: Request):
    logger.info(f'unit_status:')
    status = {
        'Resources': {
            'Focusers': list(),
            'Cameras': list(),
            'Mount': list
        }
    }
    
    for i in range(1, 4):
        for f in focusers:
            if isinstance(f, lipp.Driver):
                available = f.available
                details = f.reason_for_not_available
            status['Resources']['Focusers'].append({
                'Available': available,
                'Details': details,
            })
        
        for c in cameras:
            if isinstance(c, lipp.Driver):
                available = c.available
                details = c.reason_for_not_available
            status['Resources']['Cameras'].append({
                'Available': available,
                'Details': details,
            })

    return status