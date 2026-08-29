from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # This is where you change the model between Ollama and vLLM :)
    inference_base_url: str = "http://localhost:11434"
    inference_backend: str = "ollama"
    database_url: str = "postgresql://forge:forge@localhost:5432/forge"
    
    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()