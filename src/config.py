from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    groq_api_key: str = ""
    database_path: str = "data/cpg_sales.duckdb"
    model_path: str = "models/revenue_forecast.joblib"
    data_dir: str = "data/raw"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: str = "INFO"


settings = Settings()
