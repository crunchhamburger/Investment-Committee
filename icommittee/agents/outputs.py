"""Schemas the LLMs must fill. Kept small: every field here is either checked
by code or rendered as clearly labelled narrative."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from ..schemas import Epistemic, Recommendation, Trigger


class LLMClaim(BaseModel):
    id: str = Field(description="local id like c1")
    text: str
    epistemic: Epistemic
    citations: list[str] = Field(default_factory=list, description="evidence ids, e.g. EV-001")
    metric: Optional[str] = Field(None, description="for quantitative claims: datapoint metric name")
    value: Optional[float] = None
    unit: Optional[str] = None
    period: Optional[str] = None


class LLMAssumption(BaseModel):
    driver: str
    value: float
    epistemic: Epistemic
    basis_claims: list[str] = Field(default_factory=list)
    rationale: str


class LLMScenario(BaseModel):
    name: Literal["bear", "base", "bull"]
    probability: float = Field(ge=0, le=1)
    assumptions: list[LLMAssumption]


class AnalystDraft(BaseModel):
    thesis: str
    stance: Literal["positive", "neutral", "negative"]
    key_points: list[str]
    claims: list[LLMClaim]
    scenarios: list[LLMScenario]
    uncertainties: list[str]
    invalidation_triggers: list[Trigger] = Field(min_length=1)

    @model_validator(mode="after")
    def _scenarios(self):
        names = sorted(s.name for s in self.scenarios)
        if names != ["base", "bear", "bull"]:
            raise ValueError("exactly one bear, base and bull scenario required")
        total = sum(s.probability for s in self.scenarios)
        if abs(total - 1) > 0.01:
            raise ValueError(f"scenario probabilities must sum to 1, got {total:.3f}")
        return self


class LLMChallenge(BaseModel):
    target_role: str
    driver: str
    question: str
    counter_value: Optional[float] = None
    evidence_ids: list[str] = Field(default_factory=list)


class ChallengeSet(BaseModel):
    challenges: list[LLMChallenge] = Field(max_length=6)


class LLMResponse(BaseModel):
    challenge_id: str
    response: str
    concedes: bool
    evidence_ids: list[str] = Field(default_factory=list)


class ResponseSet(BaseModel):
    responses: list[LLMResponse]


class LLMChange(BaseModel):
    scenario: Literal["bear", "base", "bull"]
    driver: str
    new_value: float
    epistemic: Epistemic = Epistemic.ANALYST_ASSUMPTION
    reason: str
    basis_challenge_ids: list[str] = Field(default_factory=list)
    basis_evidence_ids: list[str] = Field(default_factory=list)
    basis_claims: list[str] = Field(default_factory=list)


class RevisionProposal(BaseModel):
    changes: list[LLMChange] = Field(default_factory=list)
    retained_view_reason: Optional[str] = None
    new_claims: list[LLMClaim] = Field(default_factory=list)
    scenario_probabilities: Optional[dict[str, float]] = None

    @field_validator("scenario_probabilities")
    @classmethod
    def _probs(cls, v):
        if v is None:
            return v
        if sorted(v) != ["base", "bear", "bull"] or abs(sum(v.values()) - 1) > 0.01:
            raise ValueError("scenario_probabilities must cover bear/base/bull and sum to 1")
        return v


class RiskCommentary(BaseModel):
    narrative: str
    additional_risks: list[str] = Field(default_factory=list)


class ChairDraft(BaseModel):
    primary_thesis: str
    strongest_opposing_thesis: str
    catalysts: list[str]
    key_risks: list[str]
    unresolved_questions: list[str]
    reconsideration_triggers: list[Trigger] = Field(min_length=1)
    cited_evidence: list[str] = Field(default_factory=list)
    recommendation_override: Optional[Recommendation] = None
    override_justification: Optional[str] = None
