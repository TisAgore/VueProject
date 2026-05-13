from typing import Literal

from pydantic import BaseModel, Field


ImpactLevel = Literal["critical", "high", "medium", "low"]
ProbabilityLevel = Literal["high", "medium", "low"]


class Strength(BaseModel):
    point: str
    detail: str
    impact: Literal["high", "medium", "low"]


class Weakness(BaseModel):
    point: str
    detail: str
    severity: ImpactLevel


class Risk(BaseModel):
    risk: str
    probability: ProbabilityLevel
    impact: Literal["high", "medium", "low"]
    mitigation_possible: bool


class TeamGap(BaseModel):
    gap: str
    criticality: ImpactLevel
    fixable: bool


class MarketSize(BaseModel):
    tam_assessment: str
    tam_realistic: str
    credibility: Literal["credible", "overstated", "understated"]


class CompetitiveLandscape(BaseModel):
    direct_competitors: list[str] = Field(default_factory=list)
    indirect_competitors: list[str] = Field(default_factory=list)
    differentiation_clarity: Literal["clear", "unclear", "weak"]


class ScoreBreakdown(BaseModel):
    strengths: float
    weaknesses_and_risks: float
    market: float
    team: float


class KeyConflict(BaseModel):
    conflict: str
    resolution: str


class OptimistResponse(BaseModel):
    strengths: list[Strength] = Field(default_factory=list)
    hidden_gems: list[str] = Field(default_factory=list)
    best_case_scenario: str
    score: float
    score_rationale: str


class CriticResponse(BaseModel):
    weaknesses: list[Weakness] = Field(default_factory=list)
    risks: list[Risk] = Field(default_factory=list)
    red_flags: list[str] = Field(default_factory=list)
    worst_case_scenario: str
    score: float
    score_rationale: str


class MarketResponse(BaseModel):
    market_size: MarketSize
    competitive_landscape: CompetitiveLandscape
    timing_verdict: Literal["too_early", "perfect", "too_late", "unclear"]
    timing_rationale: str
    market_tailwinds: list[str] = Field(default_factory=list)
    market_headwinds: list[str] = Field(default_factory=list)
    score: float
    score_rationale: str


class TeamResponse(BaseModel):
    team_strengths: list[str] = Field(default_factory=list)
    team_gaps: list[TeamGap] = Field(default_factory=list)
    unfair_advantage: str
    execution_signals: list[str] = Field(default_factory=list)
    founder_market_fit: Literal["strong", "medium", "weak"]
    founder_market_fit_rationale: str
    score: float
    score_rationale: str


class SynthesisResponse(BaseModel):
    executive_summary: str
    weighted_score: float
    score_breakdown: ScoreBreakdown
    key_conflicts: list[KeyConflict] = Field(default_factory=list)
    investment_recommendation: Literal["invest", "pass", "more_diligence"]
    recommendation_rationale: str
    critical_blockers: list[str] = Field(default_factory=list)
    conditions_to_invest: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)

