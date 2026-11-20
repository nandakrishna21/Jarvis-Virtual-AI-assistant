from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "JARVIS"
    host: str = "127.0.0.1"
    port: int = 8000
    database_url: str = "sqlite:///./jarvis.db"
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen3:1.7b"
    ollama_think: bool = False
    ollama_keep_alive: str = "2m"
    ollama_num_ctx: int = 2048
    ollama_num_predict: int = 512
    max_concurrent_ai_jobs: int = 1
    low_resource_mode: bool = True
    n8n_url: str = "http://127.0.0.1:5678"
    n8n_enabled: bool = True
    llm_provider: str = "ollama"  # ollama/gemini/openrouter/nvidia
    gemini_api_key: str = ""
    openrouter_api_key: str = ""
    openrouter_model: str = "google/gemini-2.0-flash-exp:free"
    nvidia_api_key: str = ""
    nvidia_model: str = "nvidia/nemotron-3.5-bolt-e4b"
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_fallback_models: str = "meta/muse-glimmer-30b,nvidia/nemotron-3.5-lightning-30b-a3b"
    api_key: str = ""  # optional local API key for mutating requests
    jarvis_api_key: str = ""  # same thing, readable as JARVIS_API_KEY from .env
    jarvis_lan_mode: bool = False  # when true the server is reachable from the LAN and every API call needs the API key
    user_name: str = "Nanda Krishna Talari"
    user_location: str = "Hyderabad, India"

settings = Settings()
