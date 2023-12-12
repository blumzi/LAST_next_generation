import uvicorn
from fastapi import FastAPI
import unit
from utils import init_log # , PrettyJSONResponse, HelpResponse, quote, Subsystem
from contextlib import asynccontextmanager
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


from server.routers import focuser, camera, mount, pswitch

def end_lifespan():
    logger.info("ending lifespan")
    unit.unit.quit()

@asynccontextmanager
async def lifespan(fast_app: FastAPI):
    pass
    yield
    end_lifespan

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
app.include_router(unit.router)

@app.get("/shutdown")
async def shutdown():
    """
    Die gracefully when asked nicely
    """
    logger.info(f"shutdown by shutdown query")
    await unit.unit.quit()
    await uvicorn_server.shutdown()
    return {"message": "Server is shutting down"}

uvicorn_server = None

if __name__ == "__main__":
    config = uvicorn.Config(app=app, host="127.0.0.1", port=8000)
    uvicorn_server = uvicorn.Server(config=config)
    uvicorn_server.run()