from fastapi import APIRouter, Request
from utils import LAST_API_ROOT, PrettyJSONResponse, init_log
import socket
import logging
from subprocess import Popen
from utils import RepeatTimer, jsonResponse
import lipp

subprocesses = list()

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
from server.routers.mount import mounts, mount_abort, mount_goTo
import sys
from pathlib import Path

parent_dir = str(Path(__file__).resolve().parent.parent)
sys.path.append(parent_dir)
from activities import Activities, Idle, UnitActivities, MountActivities, CameraActivities, FocuserActivities

mount = mounts[0]

class Unit(Activities):

    timer: RepeatTimer
    _terminating = False

    def __init__(self) -> None:
        super().__init__()
        self.timer = RepeatTimer(interval=2, function=self.on_timer)
        self.timer.name = "unit-timer-thread"
        self.timer.start()

    def on_timer(self):
        """
        Runs at pre-defined intervals.
        - Should be as short as possible.
        - Gets the current status from the various components and decides whether activities can
           be ended.
        """
        mount_st = mount.status
        #
        # If we (the unit) initiated a slew (UnitActivities.Slewing) and the mount
        #  became idle, the activity has completed
        #
        if self.is_active(UnitActivities.Slewing) and mount_st.activities == 0:
            logger.info(f"The mount arrived to destination, ending {UnitActivities.Slewing}")
            self.end_activity(UnitActivities.Slewing)

    def slew_to_coordinates(self, primary_coord: float, secondary_coord: float, coord_type: str = "eq"):
        in_progress = mount.activities()
        if in_progress != Idle:
            raise Exception(f"The mount is not idle (activities={str(in_progress)})")
        
        logger.info(f"Starting activity {UnitActivities.Slewing}")
        self.start_activity(UnitActivities.Slewing)
        mount_goTo(a1=primary_coord, a2=secondary_coord, coordtype=coord_type)

    def status(self) -> str:
        logger.info(f'unit_status:')
        
        try:
            stat = {
                'Activities': self.activities(),

                'Devices': {
                    'Focusers': list(),
                    'Cameras': list(),
                    'Mount': list()
                }
            }
            
            for f in focusers[1:5]:
                stat['Devices']['Focusers'].append({
                    'Detected': f.detected,
                    'Comms': {
                        'Responding': f.responding,
                        'LastResponse': f.last_response,
                    },
                    'Info': f.info(),
                })
                
            for c in cameras[1:5]:
                stat['Devices']['Cameras'].append({
                    'Detected': c.detected,
                    'Comms': {
                        'Responding': f.responding,
                        'LastResponse': f.last_response,
                    },
                    'Info': c.info(),
                })

            for m in mounts:
                stat['Devices']['Mount'].append({
                    'Detected': m.detected,
                    'Comms': {
                        'Responding': f.responding,
                        'LastResponse': f.last_response,
                    },
                    'Info': m.info(),
                })

            return jsonResponse({"Value": stat})
        
        except Exception as ex:
            return jsonResponse({"Exception": ex})
    
    def abort(self):

        try:
            self.start_activity(UnitActivities.Aborting)

            mount_abort();
            for c in cameras:
                c.abort()
            for f in focusers:
                f.abort()
            
            self.end_activity(UnitActivities.Aborting)
            return jsonResponse({"Value": "ok"})
        
        except Exception as ex:
            return jsonResponse({"Exception": ex})

    async def quit(self):
        logger.info("Quiting")
        self.timer.stop()
        for driver in [*focusers, *cameras, *mounts]:
            if isinstance(driver, lipp.Driver):
                await driver.quit()


unit = Unit()

# Method 'status'
@router.get(LAST_API_ROOT + 'unit/status', tags=["unit"], response_class=PrettyJSONResponse)
async def unit_status(request: Request) -> str:
    return unit.status();

# Method 'abort'
@router.get(LAST_API_ROOT + 'unit/abort', tags=["unit"], response_class=PrettyJSONResponse)
async def unit_abort(request: Request):
    unit.abort();

# Method 'quit'
@router.get(LAST_API_ROOT + 'unit/quit', tags=["unit"], response_class=PrettyJSONResponse)
async def unit_quit(request: Request):
    await unit.quit();

def start_lifespan():
    #
    # First we call the routers maker (MATLAB) which produces a python module file per
    #  each of the classes served by this FastApi server (focuser, camera, mount)
    #
    # We need to wait for it to finish before we can import the respective server.router.<class>
    #  modules
    #

    # cmd="NO_STARTUP=1 last-matlab -nodisplay -nosplash -batch 'paths = [\"AstroPack/matlab/base\", \"AstroPack/matlab/util\", \"LAST/LAST_Handle\", \"LAST/LAST_Api\"]; top = fullfile(getenv(\"HOME\"), \"matlab\"); for p = 1:numel(paths); addpath(fullfile(top, paths(p))); end; obs.api.ApiBase.makeAuxiliaryFiles(); exit(0)'"

    cmd="last-matlab -nodisplay -nosplash -batch 'obs.api.ApiBase.makeAuxiliaryFiles; exit'"
    logger.info(f'calling MATLAB FastApi routers maker with cmd="{cmd}"')
    routers_maker = Popen(args=cmd, shell=True)
    logger.info(f'Waiting for MATLAB FastApi routers maker')
    routers_maker.wait()
    if routers_maker.returncode == 0:
        logger.info('FastApi routers maker succeeded!')
    else:
        logger.error(f'FastApi routers maker died with rc={routers_maker.returncode}')
        exit(routers_maker.returncode)

def end_lifespan():
    logger.info(f"end_lifespan:") 
    unit.quit()