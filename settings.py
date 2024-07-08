from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="allow")

    DB_NAME: str
    DB_COLLECTION: str
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str = "localhost"

    API_TOKEN: str

    ADMIN_ID: int
    ADMIN_NAME: str

    @computed_field
    def db_url(self) -> str:
        return f"mongodb://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:27017/"


settings = Settings()
