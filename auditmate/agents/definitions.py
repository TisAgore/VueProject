from dataclasses import dataclass

from pydantic import BaseModel

from auditmate.models.responses import CriticResponse, MarketResponse, OptimistResponse, TeamResponse
from auditmate.agents.prompt_loader import load_prompt


@dataclass(frozen=True)
class AgentDefinition:
    name: str
    emoji: str
    system_prompt: str
    response_model: type[BaseModel]
    temperature: float

AGENT_DEFINITIONS: dict[str, AgentDefinition] = {
    "optimist": AgentDefinition(
        name="Венчурный Оптимист",
        emoji="🚀",
        temperature=0.75,
        response_model=OptimistResponse,
        system_prompt=load_prompt("optimist"),
    ),
    "critic": AgentDefinition(
        name="Скептичный Аналитик",
        emoji="🔍",
        temperature=0.4,
        response_model=CriticResponse,
        system_prompt=load_prompt("critic"),
    ),
    "market_analyst": AgentDefinition(
        name="Рыночный Аналитик",
        emoji="📊",
        temperature=0.3,
        response_model=MarketResponse,
        system_prompt=load_prompt("market_analyst"),
    ),
    "team_evaluator": AgentDefinition(
        name="Эксперт по Командам",
        emoji="👥",
        temperature=0.5,
        response_model=TeamResponse,
        system_prompt=load_prompt("team_evaluator"),
    )
}


SYNTHESIZER_SYSTEM = load_prompt("synthesizer")
