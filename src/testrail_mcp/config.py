from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    testrail_url: str
    testrail_email: str
    testrail_api_key: str
    transport: str = "http"
    port: int = 8000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    @field_validator("testrail_url")
    @classmethod
    def strip_trailing_slash(cls, v: str) -> str:
        return v.rstrip("/")

    @field_validator("transport")
    @classmethod
    def validate_transport(cls, v: str) -> str:
        if v not in ("http", "stdio"):
            raise ValueError("TRANSPORT must be 'http' or 'stdio'")
        return v
