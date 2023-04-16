import enum


__all__ = (
    'ChatState', 'ChatUserRole'
)


class ChatState(enum.IntEnum):
    ACTIVE = 1
    FOR_FAVORITE = 3
    ARCHIVE = 4
    FAVORITE = 5
    DELETED = 6


class ChatUserRole(enum.IntEnum):
    CREATOR = 1
    ADMIN = 2
    USER = 3
    ONLY_FOR_DATA = 4
