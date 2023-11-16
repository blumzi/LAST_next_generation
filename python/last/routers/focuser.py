from fastapi import APIRouter, Request
from utils import LAST_API_ROOT, PrettyJSONResponse, equipment_ids, Equipment, default_port, init_log, ValidEquipId
import socket
from forwarder import Forwarder
from lipp import Response
import logging
import lipp

logger = logging.getLogger('focuser-driver')
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

drivers = [None, None, None, None, None]
for id in equipment_ids[this_side]:
    drivers[id] = lipp.Driver(Equipment.Focuser, id)

for id in equipment_ids[peer_side]:
    drivers[id] = Forwarder(address=peer_hostname, port=default_port, equip=Equipment.Focuser, equip_id=id)

@router.get('/' + LAST_API_ROOT + '/focuser/{id}/position', response_class=PrettyJSONResponse)
async def focuser_get_position(id: ValidEquipId, request: Request):
    id = int(id)
    logger.info(f"focuser_get: id={id}, position")
    return await drivers[id].get(method='position', params=None)
    
@router.get('/' + LAST_API_ROOT + '/focuser/{id}/move', response_class=PrettyJSONResponse)
async def focuser_move(id: ValidEquipId, position: float, request: Request):
    id = int(id)
    logger.info(f"focuser_get: id={id}, move, params={request.path_params}")
    return await drivers[id].get('move', request.query_params)
    

# @router.put(LAST_API_ROOT + 'test/{id}/{method}', response_class=PrettyJSONResponse)
# async def focuser_put(id: str, method: str, request: Request):
#     id = int(id)
#     logger.info(f"focuser_put: id={id}, peer_ids={equipment_ids[peer_side]}, id={id}, method='{method}', params={request.query_params}")
#     if id in equipment_ids[peer_side]:
#         return await forwarders[id].put(request.query_params)
#     else:
#         raise Exception(f"don't know how to handle id={id}")
