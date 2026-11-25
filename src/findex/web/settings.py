from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    index_path: Path = Path("index.bin")
    corpus_path: Path = Path("data/crawl.jsonl")
    log_level: str = "INFO"
    port: int = Field(default=8000, ge=1, le=65535)
