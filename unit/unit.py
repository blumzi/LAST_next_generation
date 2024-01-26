from fastapi import APIRouter, Request
from utils import LAST_API_ROOT, PrettyJSONResponse, init_log
import socket
import logging
from utils import RepeatTimer, jsonResponse
import lipp
import os
from typing import List
from validations import ValidCoordSystems
from telescope import Telescope
from concurrent.futures import ThreadPoolExecutor, TimeoutError

from server.routers.camera import cameras
from server.routers.focuser import focusers
from server.routers.mount import mounts, mount_abort, mount_goTo
import sys
from pathlib import Path
from activities import Activities, UnitActivities, Idle

subprocesses = list()

logger = logging.getLogger('unit-FastApi')
init_log(logger)

unit_router = APIRouter()

hostname = socket.gethostname()
this_side = 'x'
if hostname.startswith('last'):
    this_side = hostname[-1]
if this_side == 'w':
    peer_side = 'e'
else:
    peer_side = 'w'
peer_hostname = hostname[:-1] + peer_side

parent_dir = str(Path(__file__).resolve().parent.parent)
sys.path.append(parent_dir)

mount = mounts[0]
telescopes: List[Telescope] = [
    None,  # skip zero, go MATLAB :-)
    Telescope(1, focuser=focusers[1], camera=cameras[1]),
    Telescope(2, focuser=focusers[2], camera=cameras[2]),
    Telescope(3, focuser=focusers[3], camera=cameras[3]),
    Telescope(4, focuser=focusers[4], camera=cameras[4]),
    ]


class Unit(Activities):

    timer: RepeatTimer
    _terminating = False
    _status_timeout: int  # how many seconds to wait for status requests

    def __init__(self, status_timeout=5) -> None:
        super().__init__()
        self._status_timeout = status_timeout
        self.timer = RepeatTimer(name="unit-timer-thread", interval=2, function=self.on_timer)
        self.timer.start()

    def on_timer(self):
        """
        Runs at pre-defined intervals.
        - Should be as short as possible.
        - Gets the current status from the various components and decides whether activities can
           be ended.
        """
        mount_status = None
        #
        # If we (the unit) initiated a slew (UnitActivities.Slewing) and the mount
        #  became idle, the activity has completed
        #
        if self.is_active(UnitActivities.Slewing):
            if mount_status is None:
                mount_status = mount.status()

            if mount_status.Activities == Idle:
                logger.info(f"The mount arrived to destination, ending {UnitActivities.Slewing}")
                self.end_activity(UnitActivities.Slewing)

    def slew_to_coordinates(self, primary_coord: float, secondary_coord: float,
                            coord_system: ValidCoordSystems = ValidCoordSystems.eq):
        mount_status = mount.status()
        if mount_status.Activities != Idle:
            raise Exception(f"The mount is not Idle (activities={str(mount_status.Activities)})")
        
        logger.info(f"Starting activity {UnitActivities.Slewing}")
        self.start_activity(UnitActivities.Slewing)
        mount_goTo(a1=primary_coord, a2=secondary_coord, coordtype=coord_system)

    def status(self) -> str:
        logger.info(f'unit_status:')
        
        try:
            stat = {'activities': self.activities, 'devices': dict()}
            stat['devices']['telescopes'] = list()

            with ThreadPoolExecutor(thread_name_prefix=f"unit-status-fetcher-") as executor:
                for t in telescopes[1:5]:
                    t.focuser_status = None
                    t.camera_status = None

                    t.focuser_future = executor.submit(t.focuser.status)
                    t.camera_future = executor.submit(t.camera.status)

                # mount_status = None
                mount_future = executor.submit(mount.status)

                for t in telescopes[1:5]:
                    try:
                        t.focuser_status = t.focuser_future.result(timeout=self._status_timeout)
                    except TimeoutError:
                        t.focuser_status = None
                    
                    try:
                        t.camera_status = t.camera_future.result(timeout=self._status_timeout)
                    except TimeoutError:
                        t.camera_status = None

                try:
                    mount_status = mount_future.result(timeout=self._status_timeout)
                except TimeoutError:
                    mount_status = None

            for t in telescopes[1:5]:
                stat['devices']['telescopes'].append({
                    'info': t.info(),
                    'status': t.status(),
                    'focuser': {
                        'info': t.focuser.info(),
                        'status': t.focuser_status,
                    },
                    'camera': {
                        'info': t.camera.info(),
                        'status': t.camera_status,
                    }
                })

            stat['devices']['mount'] = {
                'info': mount.info(),
                'status': mount_status
            }

            return jsonResponse({"Value": stat})
        
        except Exception as ex:
            return jsonResponse({"Exception": ex})
    
    def abort(self):

        try:
            self.start_activity(UnitActivities.Aborting)

            mount_abort()
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
        if self.timer is not None:
            self.timer.stop()
        for driver in [*focusers, *cameras, *mounts]:
            if isinstance(driver, lipp.Driver):
                await driver.quit()

        cmd = "pkill -f 'obs.api.Lipp.*\.loop()'"
        logger.info("Killing LIPP processes with command: \"%s\"", cmd)
        os.system(cmd)


unit = Unit()


# Method 'status'
@unit_router.get(LAST_API_ROOT + 'unit/status', tags=["unit"], response_class=PrettyJSONResponse)
async def unit_status(request: Request) -> str:
    return unit.status()


# Method 'abort'
@unit_router.get(LAST_API_ROOT + 'unit/abort', tags=["unit"], response_class=PrettyJSONResponse)
async def unit_abort(request: Request):
    unit.abort()


# Method 'quit'
@unit_router.get(LAST_API_ROOT + 'unit/quit', tags=["unit"], response_class=PrettyJSONResponse)
async def unit_quit():
    await unit.quit()


# Method 'slew_to_coordinates
@unit_router.get(LAST_API_ROOT + 'unit/slew_to_coordinates', tags=["unit"], response_class=PrettyJSONResponse)
async def unit_slew_to_coordinates(primary_coord: float, secondary_coord: float, coord_system: ValidCoordSystems):
    await unit.slew_to_coordinates(primary_coord=primary_coord, secondary_coord=secondary_coord,
                                   coord_system=coord_system)


# def start_lifespan():
#     #
#     # First we call the routers maker (MATLAB) which produces a python module file per
#     #  each of the classes served by this FastApi server (focuser, camera, mount)
#     #
#     # We need to wait for it to finish before we can import the respective server.unit_router.<class>
#     #  modules
#     #

#     cmd="last-matlab -nodisplay -nosplash -batch 'obs.api.ApiBase.makeAuxiliaryFiles; exit'"
#     logger.info(f'calling MATLAB FastApi routers maker with cmd="{cmd}"')
#     routers_maker = Popen(args=cmd, shell=True)
#     logger.info(f'Waiting for MATLAB FastApi routers maker')
#     routers_maker.wait()
#     if routers_maker.returncode == 0:
#         logger.info('FastApi routers maker succeeded!')
#     else:
#         logger.error(f'FastApi routers maker died with rc={routers_maker.returncode}')
#         exit(routers_maker.returncode)
#
#
# def end_lifespan():
#     logger.info(f"end_lifespan:")
#     unit.quit()
