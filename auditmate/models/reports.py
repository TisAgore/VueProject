from dataclasses import dataclass
from typing import Optional


@dataclass
class AgentResult:
    agent_key: str
    agent_name: str
    emoji: str
    model_used: str
    provider: str
    raw_response: str
    parsed: Optional[dict]
    duration_ms: int
    error: Optional[str] = None


@dataclass
class CommitteeReport:
    pitch_excerpt: str
    model_key: str
    sequential: bool
    agent_results: list[AgentResult]
    synthesis: Optional[dict]
    total_duration_ms: int
    timestamp: str

