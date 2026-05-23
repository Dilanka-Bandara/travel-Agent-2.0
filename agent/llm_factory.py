"""
LLM factory. One function returns the configured CrewAI LLM. Switching from
local Ollama to a cheap cloud model is a pure config change -- no code edits.
"""
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
        return LLM(
            model=s.llm_model,          # e.g. "gpt-4o-mini"
            api_key=s.openai_api_key,
            temperature=s.llm_temperature,
        )

    if s.llm_provider == "gemini":
        return LLM(
            model=s.llm_model,          # e.g. "gemini/gemini-2.0-flash"
            api_key=s.gemini_api_key,
            temperature=s.llm_temperature,
        )

    raise ValueError(f"Unknown LLM provider: {s.llm_provider}")
