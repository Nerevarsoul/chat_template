from pydantic import BaseSettings


class WebSettings(BaseSettings):

    host: str = "0.0.0.0"
    port: int = 8061
