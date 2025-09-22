from typing import Optional
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Endpoint(BaseSettings):
    url: str
    port: int


class LLM(BaseSettings):
    url: str
    name: str


class Settings(BaseSettings):
    env_path: str = "src/.env"

    model_config = SettingsConfigDict(env_file=env_path, env_nested_delimiter="__")

    qdrant: Endpoint
    mongo: Endpoint
    ingest: Endpoint
    llm: LLM
    sparse: Endpoint
    dense: Endpoint

    dense_embedding_dimension: int
    dense_embedding_window: int

    sparse_model_name: str

    llm_chat_history_limit: Optional[int] = None

    qdrant_key: Optional[SecretStr] = None
    mongo_password: Optional[SecretStr] = None
    mongo_username: Optional[SecretStr] = None
    admin_password: Optional[SecretStr] = None
    secret_key: Optional[SecretStr] = None


if __name__ == "__main__":
    settings = Settings()
    print(settings.model_dump())
