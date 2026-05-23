"""
Agent definitions. Same two-agent idea you designed (a pacing architect and an
experience/accommodation specialist), but tools are assembled dynamically from
whatever grounding sources are enabled in config.
"""
from crewai import Agent
from app.config.settings import get_settings
from app.services.llm_factory import build_llm
from app.tools.web_search import web_search
from app.tools.aurelia_backend import hotel_availability


def _enabled_tools():
    s = get_settings()
    tools = []
    if s.enable_web_search:
        tools.append(web_search)
    if s.enable_aurelia_backend:
        tools.append(hotel_availability)
    return tools


def build_route_planner() -> Agent:
    return Agent(
        role="Expert Travel Route Architect",
        goal="Split a journey into evenly paced daily segments and pick the best overnight towns.",
        backstory=(
            "You are a master road-trip planner. You know how to pace a trip so each "
            "day's drive is reasonable. For an N-day trip you find natural overnight "
            "stopping towns that break the journey evenly."
        ),
        verbose=True,
        allow_delegation=False,
        tools=_enabled_tools(),
        llm=build_llm(),
    )


def build_experience_specialist() -> Agent:
    return Agent(
        role="Local Experience & Accommodation Specialist",
        goal="Find vibe-matching activities and real, group-appropriate hotels for each daily stop.",
        backstory=(
            "You are a meticulous local guide. You know what to do along each stretch of "
            "road, and you are careful that every hotel can actually accommodate the "
            "traveler's specific group size. You prefer real, verifiable options over guesses."
        ),
        verbose=True,
        allow_delegation=False,
        tools=_enabled_tools(),
        llm=build_llm(),
    )
