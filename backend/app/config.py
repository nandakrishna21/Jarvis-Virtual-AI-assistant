from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _clean_key(value: str) -> str:
    """Remove smart quotes and other non-ASCII characters from pasted keys.

    Copying a key from a PDF or a chat bubble often adds Windows smart quotes
    (U+201C/U+201D). HTTP headers must be ASCII, so those characters break every
    provider call. They are stripped here instead of failing at request time.
    """
    if not value:
        return value
    cleaned = "".join(ch for ch in value if 32 <= ord(ch) < 127)
    return cleaned.strip()


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
    gemini_model: str = "gemini-3.5-flash"
    openrouter_api_key: str = ""
    openrouter_model: str = "google/gemini-2.0-flash-exp:free"
    nvidia_api_key: str = ""
    nvidia_model: str = "nvidia/nemotron-3.5-bolt-e4b"
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_fallback_models: str = "meta/muse-glimmer-30b,nvidia/nemotron-3.5-lightning-30b-a3b"
    # Voice input engine: auto (Gemini if key present, else Whisper) | gemini | whisper
    stt_engine: str = Field("auto", validation_alias=AliasChoices("JARVIS_STT_ENGINE", "stt_engine"))
    gemini_stt_model: str = Field("gemini-3.5-flash", validation_alias=AliasChoices("GEMINI_STT_MODEL", "gemini_stt_model"))
    # Apify job scraping (optional). The actor must accept query/location/count.
    apify_token: str = Field("", validation_alias=AliasChoices("APIFY_API_KEY", "APIFY_TOKEN", "apify_token"))
    apify_actor: str = Field(
        "curious_coder/indeed-scraper",
        validation_alias=AliasChoices("APIFY_ACTOR", "apify_actor"),
    )
    apify_country: str = Field("in", validation_alias=AliasChoices("APIFY_COUNTRY", "apify_country"))
    apify_max_items: int = Field(20, validation_alias=AliasChoices("APIFY_MAX_ITEMS", "apify_max_items"))
    apify_per_minute: int = Field(3, validation_alias=AliasChoices("APIFY_PER_MINUTE", "apify_per_minute"))
    apify_input_json: str = Field("", validation_alias=AliasChoices("APIFY_INPUT_JSON", "apify_input_json"))
    api_key: str = ""  # optional local API key for mutating requests
    jarvis_api_key: str = ""  # same thing, readable as JARVIS_API_KEY from .env
    jarvis_lan_mode: bool = False  # when true the server is reachable from the LAN and every API call needs the API key
    user_name: str = "Nanda Krishna Talari"
    user_location: str = "Hyderabad, India"

    # Deployment / public demo (both DEMO_MODE and JARVIS_DEMO_MODE are accepted)
    demo_mode: bool = Field(False, validation_alias=AliasChoices("demo_mode", "JARVIS_DEMO_MODE"))
    cors_origins: str = Field(
        "http://127.0.0.1:5173,http://localhost:5173",
        validation_alias=AliasChoices("cors_origins", "JARVIS_CORS_ORIGINS"),
    )
    backend_url: str = ""  # optional public URL, used by health/status output

    # Abuse protection (per client IP, per minute). Set 0 to disable a bucket.
    rate_limit_chat_per_minute: int = Field(
        30, validation_alias=AliasChoices("rate_limit_chat_per_minute", "JARVIS_RATE_LIMIT_CHAT_PER_MINUTE")
    )
    rate_limit_voice_per_minute: int = Field(
        20, validation_alias=AliasChoices("rate_limit_voice_per_minute", "JARVIS_RATE_LIMIT_VOICE_PER_MINUTE")
    )
    rate_limit_api_per_minute: int = Field(
        240, validation_alias=AliasChoices("rate_limit_api_per_minute", "JARVIS_RATE_LIMIT_API_PER_MINUTE")
    )
    max_message_chars: int = Field(
        4000, validation_alias=AliasChoices("max_message_chars", "JARVIS_MAX_MESSAGE_CHARS")
    )

    @field_validator("nvidia_api_key", "gemini_api_key", "openrouter_api_key", "apify_token",
                     "api_key", "jarvis_api_key", mode="before")
    @classmethod
    def _sanitize_keys(cls, value):
        if isinstance(value, str):
            return _clean_key(value)
        return value

settings = Settings()
