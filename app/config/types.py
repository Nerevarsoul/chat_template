from pydantic.networks import AnyUrl


class AsyncDBDsn(AnyUrl):
    allowed_schemes = {"postgres", "postgresql", "postgresql+asyncpg"}
    user_required = True

    @property
    def clear_dsn(self) -> str:
        return f"{self.scheme}://{self.user}:{self.password}" f"@{self.host}:{self.port}{self.path}"

    @property
    def server_settings(self) -> None | dict[str, str]:
        if not self.query:
            return None
        settings = {
            key_value[0]: key_value[1]
            for param in self.query.split("&")
            if (key_value := param.split("="))
        }
        return settings if settings else None
