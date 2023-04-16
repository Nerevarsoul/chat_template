__all__ = ["application", "cache", "socketio"]


from .application import AppSettings
from .cache import CacheSettings
from .db import DBSettings
from .socketio import SocketioSettings
from .web import WebSettings


application: AppSettings = AppSettings()
cache: CacheSettings = CacheSettings()
database: DBSettings = DBSettings()
socketio: SocketioSettings = SocketioSettings()
web: WebSettings = WebSettings()


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[%(asctime)s %(levelname)s] [%(request_id)s] %(name)s | %(message)s",
        },
        "json": {
            "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(levelname)s %(request_id)s %(name)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "level": application.log_level,
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "app": {
            "handlers": ["console"],
            "level": application.log_level,
            "propagate": False,
        },
        "uvicorn.access": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "": {
            "handlers": ["console"],
            "level": "WARNING",
        },
    },
}
