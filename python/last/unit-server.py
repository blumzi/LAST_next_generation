import uvicorn
from fastapi import FastAPI, Request
# from unit import Unit
import test
from utils import init_log # , PrettyJSONResponse, HelpResponse, quote, Subsystem
import inspect
# from openapi import make_openapi_schema
import logging
from contextlib import asynccontextmanager
# import psutil
import os
# from fastapi.responses import RedirectResponse
# from fastapi.staticfiles import StaticFiles
from socket import gethostname

import routers.focuser

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

app.include_router(routers.focuser.router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)