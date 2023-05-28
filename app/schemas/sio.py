import enum


class SioEvents(enum.StrEnum):
    USER_MISSING = "srv:user:missing"
    USER_NOT_FOUND = "srv:user:not found"
