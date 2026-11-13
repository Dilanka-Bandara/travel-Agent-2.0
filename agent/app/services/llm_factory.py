"""
LLM factory. One function returns the configured CrewAI LLM. Switching from
local Ollama to a cheap cloud model is a pure config change -- no code edits.
"""
import os
from crewai import LLM
from app.config.settings import get_settings


def build_llm() -> LLM:
    s = get_settings()

    if s.llm_provider == "ollama":
        return LLM(
            model=s.llm_model,          # e.g. "ollama/qwen2.5:7b"
            base_url=s.llm_base_url,
            timeout=s.llm_timeout,
            temperature=s.llm_temperature,
        )

    if s.llm_provider == "openai":
        api_key = s.openai_api_key.get_secret_value() if hasattr(s.openai_api_key, 'get_secret_value') else s.openai_api_key
        os.environ["OPENAI_API_KEY"] = api_key
        return LLM(
            model=s.llm_model,          # e.g. "gpt-4o-mini"
            api_key=api_key,
            temperature=s.llm_temperature,
        )

    if s.llm_provider == "gemini":
        api_key = s.gemini_api_key.get_secret_value() if hasattr(s.gemini_api_key, 'get_secret_value') else s.gemini_api_key
        os.environ["GEMINI_API_KEY"] = api_key
        return LLM(
            model=s.llm_model,          # e.g. "gemini/gemini-2.0-flash"
            api_key=api_key,
            temperature=s.llm_temperature,
        )

    if s.llm_provider == "groq":
        # Safely extract the key (handles both normal strings and SecretStr)
        api_key = s.groq_api_key.get_secret_value() if hasattr(s.groq_api_key, 'get_secret_value') else s.groq_api_key
        
        # CRITICAL FIX: Force the key into the system environment for LiteLLM
        os.environ["GROQ_API_KEY"] = api_key
        
        return LLM(
            model=s.llm_model,          # e.g. "groq/llama-3.3-70b-versatile"
            api_key=api_key,
            temperature=s.llm_temperature,
        )

    raise ValueError(f"Unknown LLM provider: {s.llm_provider}")