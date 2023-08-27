from pydantic import BaseModel


class Result(BaseModel):
    success: bool


class ChatApiResponse(BaseModel):
    result: Result
