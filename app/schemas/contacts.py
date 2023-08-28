from enum import StrEnum

from pydantic import BaseModel


class PlatformName(StrEnum):
    IOS = "ios"
    ANDROID = "android"
    HUAWEI = "huawei"


class TokenData(BaseModel):
    token: str
    device_type: PlatformName
