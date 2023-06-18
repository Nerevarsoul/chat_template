#!/usr/bin/env python

import uvicorn
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from socketio import ASGIApp
from uvicorn.loops.uvloop import uvloop_setup

from app import api, config
from app.api.exception_handlers import request_validation_exception_handler
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
fastapi_app.add_exception_handler(RequestValidationError, request_validation_exception_handler)

app = ASGIApp(sio, fastapi_app)


def main() -> None:
    uvicorn.run(app, host=config.web.host, port=config.web.port, access_log=True)


if __name__ == "__main__":
    main()
