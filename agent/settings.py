"""
Central configuration. Everything that changes between environments
(local Ollama vs cloud, which backend URL, timeouts, API keys) lives here
and is driven by environment variables so nothing is hardcoded.

Swapping the LLM from local to cloud is a one-line .env change:
    LLM_PROVIDER=ollama   -> runs llama/qwen/mistral on your PC
    LLM_PROVIDER=openai   -> runs a cheap hosted model
    LLM_PROVIDER=gemini   -> runs Gemini Flash
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ---- LLM selection ----
    llm_provider: str = "ollama"          # ollama | openai | gemini
    llm_model: str = "ollama/qwen2.5:7b"  # see notes in README on model choice
    llm_base_url: str = "http://localhost:11434"
    llm_timeout: int = 600
    llm_temperature: float = 0.3          # lower = more reliable structured output

    # API keys (only needed for cloud providers; safe to leave blank for ollama)
    openai_api_key: str = ""
    gemini_api_key: str = ""

    # ---- Grounding sources ----
    # Toggle each data source on/off without touching code.
    enable_web_search: bool = True
    enable_aurelia_backend: bool = False
    enable_maps_api: bool = False

    aurelia_base_url: str = "http://localhost:5000"
    aurelia_api_key: str = ""

    google_maps_api_key: str = ""

    # ---- Reliability ----
    max_validation_retries: int = 2       # repair attempts on malformed JSON
    routes_per_trip: int = 3              # generated one-at-a-time, then assembled


@lru_cache
def get_settings() -> Settings:
    return Settings()
