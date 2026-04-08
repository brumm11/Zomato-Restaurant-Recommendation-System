from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "restaurant-recommendation-service"
    app_env: str = "development"
    llm_api_key: str = Field(default="", validation_alias=AliasChoices("GROQ_API_KEY", "LLM_API_KEY"))
    llm_model: str = Field(
        default="llama-3.3-70b-versatile",
        validation_alias=AliasChoices("GROQ_MODEL", "LLM_MODEL"),
    )
    data_source: str = "huggingface:ManikaSaini/zomato-restaurant-recommendation"
    normalized_data_path: str = Field(
        default="artifacts/data/restaurants_normalized.jsonl",
        validation_alias=AliasChoices("NORMALIZED_DATA_PATH", "normalized_data_path"),
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
