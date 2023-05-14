#!/usr/bin/env python
import asyncio

import uvicorn
from fastapi import FastAPI
from socketio import ASGIApp
from uvicorn.loops.uvloop import uvloop_setup

from app import api, config
from app.db.registry import registry
from app.sio import sio

uvloop_setup()


fastapi_app = FastAPI(
    title=config.application.name,
    version=config.application.version,
    debug=config.application.debug,
    docs_url=config.application.docs_url,
    root_path=config.application.root_path,
)
fastapi_app.include_router(api.router, prefix="/api")

fastapi_app.add_event_handler("startup", registry.setup)
fastapi_app.add_event_handler("shutdown", registry.close)

app = ASGIApp(sio, fastapi_app)


def main():
    uvicorn.run(app, host=config.web.host, port=config.web.port, access_log=True)


if __name__ == "__main__":
    main()
