import uvicorn
from fastapi import FastAPI
# from unit import Unit
from utils import init_log # , PrettyJSONResponse, HelpResponse, quote, Subsystem
# from openapi import make_openapi_schema
from contextlib import asynccontextmanager
# import psutil
# from fastapi.responses import RedirectResponse
# from fastapi.staticfiles import StaticFiles
from socket import gethostname
import logging
from subprocess import Popen

logger = logging.getLogger('last-unit-server')
init_log(logger)

#
# First we call the routers maker (MATLAB) which produces a python module file per
#  each of the classes served by this FastApi server (focuser, camera, mount)
#
# We need to wait for it to finish before we can import the respective server.router.<class>
#  modules
#
cmd=f'last-matlab -nodisplay -nosplash -batch "obs.api.ApiBase.makeAuxiliaryFiles()"'
# logger.info(f'calling MATLAB FastApi routers maker with cmd="{cmd}"')
routers_maker = Popen(args=cmd, shell=True)
logger.info(f'Waiting for MATLAB FastApi routers maker')
routers_maker.wait()
if routers_maker.returncode == 0:
    logger.info('FastApi routers maker succeeded!')
else:
    logger.error(f'FastApi routers maker died with rc={routers_maker.returncode}')
    exit(routers_maker.returncode)


from server.routers import focuser, camera, mount
import unit

@asynccontextmanager
async def lifespan(fast_app: FastAPI):
    # unit.start_lifespan()
    pass
    yield
    pass
    # unit.end_lifespan()


app = FastAPI(
    title=f'LAST Unit Api server on {gethostname()}',
    docs_url='/docs',
    redocs_url='/redocs',
    lifespan=lifespan,
    openapi_url='/openapi.json')

app.include_router(focuser.router)
app.include_router(camera.router)
app.include_router(mount.router)
app.include_router(unit.router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)