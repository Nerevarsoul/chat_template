from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


async def request_validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    message = {error["loc"][1]: error["msg"] for error in exc.errors()}
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": message},
    )
