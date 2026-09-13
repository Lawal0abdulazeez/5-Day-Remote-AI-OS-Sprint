import os
from pydantic import BaseModel


class AppConfig(BaseModel):
    app_name: str = "TalentOps AI OS Mini"
    version: str = "1.0.0"
    host: str = os.getenv("HOST", "127.0.0.1")
    port: int = int(os.getenv("PORT", "8080"))
    debug: bool = os.getenv("DEBUG", "true").lower() == "true"
    llm_provider: str = os.getenv("LLM_PROVIDER", "mock").lower()
    data_dir: str = os.getenv("DATA_DIR", "data")
    max_file_size_mb: int = int(os.getenv("MAX_FILE_SIZE_MB", "15"))


config = AppConfig()
