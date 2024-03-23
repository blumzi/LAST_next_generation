import datetime
import os
import signal

import uvicorn
from fastapi import FastAPI
from utils import init_log  # , PrettyJSONResponse, HelpResponse, quote, Subsystem
from contextlib import asynccontextmanager
from socket import gethostname
import logging
from subprocess import Popen

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from unit import unit_quit, unit_router
from server.routers import focuser, camera, mount, pswitch

logger = logging.getLogger('last-unit-server')
init_log(logger)

#
# First we call the routers maker (MATLAB) which produces a python module file per
#  each of the classes served by this FastApi server (focuser, camera, mount)
#
# We need to wait for it to finish before we can import the respective server.unit_router.<class>
#  modules
#

cmd = "last-matlab -batch 'obs.api.ApiBase.makeAuxiliaryFiles; exit(0)'"
logger.info(f'calling MATLAB FastApi routers maker with cmd="{cmd}"')
routers_maker = Popen(args=cmd, shell=True)
logger.info(f'Waiting for MATLAB FastApi routers maker')
routers_maker.wait()
if routers_maker.returncode == 0:
    logger.info('FastApi routers maker succeeded!')
else:
    logger.error(f'FastApi routers maker died with rc={routers_maker.returncode}')
    exit(routers_maker.returncode)


async def end_lifespan():
    logger.info("ending lifespan")
    await unit_quit()


@asynccontextmanager
async def lifespan(fast_app: FastAPI):
    pass
    yield
    await end_lifespan()

app = FastAPI(
    title=f'LAST Unit Api server on {gethostname()}',
    docs_url='/docs',
    redocs_url='/redocs',
    lifespan=lifespan,
    openapi_url='/openapi.json')

app.include_router(pswitch.router)
app.include_router(focuser.router)
app.include_router(camera.router)
app.include_router(mount.router)
app.include_router(unit_router)


@app.get("/shutdown", tags=['last-unit-service'])
async def shutdown():
    """
    Die gracefully when asked nicely
    """
    logger.info(f"shutdown by shutdown query")
    await unit_quit()
    uvicorn_server.should_exit = True
    logger.info('Committing suicide :-)')
    os.kill(os.getpid(), signal.SIGTERM)
    return {"message": "Server is shutting down"}

uvicorn_server = None

if __name__ == "__main__":
    config = uvicorn.Config(app=app, host="0.0.0.0", port=8000)
    uvicorn_server = uvicorn.Server(config=config)
    uvicorn_server.run()
