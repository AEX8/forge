from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # This is where you change the model between Ollama and vLLM :)
    inference_base_url: str = "http://localhost:11434"
    inference_backend: str = "ollama"

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()