"""Typed schemas shared across the system.

Design rule: anything that can move a number must be a typed object with
provenance. Free text is allowed for narrative only and never feeds the
valuation engine.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def stable_hash(obj) -> str:
    """Deterministic short hash of any JSON-serialisable object."""
    if isinstance(obj, BaseModel):
        obj = obj.model_dump(mode="json")
    payload = json.dumps(obj, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=False)


# --------------------------------------------------------------------------- #
# Epistemic status: the six classes the brief asks us to keep apart.
# --------------------------------------------------------------------------- #
class Epistemic(str, Enum):
    VERIFIED_FACT = "verified_fact"            # reported historical figure, primary source
    MANAGEMENT_GUIDANCE = "management_guidance"
    THIRD_PARTY_ESTIMATE = "third_party_estimate"
    ANALYST_ASSUMPTION = "analyst_assumption"  # a forecast the analyst owns
    MODEL_DERIVED = "model_derived"            # produced by deterministic code
    SPECULATION = "speculation"                # unresolved; may never enter valuation


class SourceTier(str, Enum):
    PRIMARY = "primary"      # issuer filings, issuer releases, exchange data
    SECONDARY = "secondary"  # news, sell-side, industry research, blogs


class SourceKind(str, Enum):
    SEC_FILING = "sec_filing"
    EARNINGS_RELEASE = "earnings_release"
    INVESTOR_PRESENTATION = "investor_presentation"
    TRANSCRIPT = "transcript"
    MARKET_DATA = "market_data"
    INDUSTRY_RESEARCH = "industry_research"
    NEWS = "news"
    MACRO = "macro"
    OTHER = "other"


# --------------------------------------------------------------------------- #
# Evidence
# --------------------------------------------------------------------------- #
UNIT_SCALE = {
    "USD": 1.0, "USD_k": 1e3, "USD_m": 1e6, "USD_bn": 1e9,
    "shares": 1.0, "shares_m": 1e6,
    "MW": 1.0, "GW": 1e3,
    "fraction": 1.0, "pct": 0.01,
    "x": 1.0, "USD_per_hour": 1.0, "USD_per_MWh": 1.0, "count": 1.0,
    "years": 1.0, "kW": 1.0,
}
UNIT_FAMILY = {
    "USD": "USD", "USD_k": "USD", "USD_m": "USD", "USD_bn": "USD",
    "shares": "shares", "shares_m": "shares",
    "MW": "MW", "GW": "MW",
    "fraction": "fraction", "pct": "fraction",
    "x": "x", "USD_per_hour": "USD_per_hour", "USD_per_MWh": "USD_per_MWh",
    "count": "count", "years": "years", "kW": "kW",
}


def normalise(value: float, unit: str) -> tuple[float, str]:
    if unit not in UNIT_SCALE:
        raise ValueError(f"unknown unit {unit!r}; allowed: {sorted(UNIT_SCALE)}")
    return value * UNIT_SCALE[unit], UNIT_FAMILY[unit]


class DataPoint(Strict):
    """A single structured number inside a source document."""
    metric: str
    value: float
    unit: str
    period: str                       # e.g. "FY2025", "2026-06-30"
    basis: Epistemic                  # what the *source* says this number is

    @field_validator("unit")
    @classmethod
    def _known_unit(cls, v: str) -> str:
        if v not in UNIT_SCALE:
            raise ValueError(f"unknown unit {v!r}")
        return v

    @field_validator("value", mode="before")
    @classmethod
    def _no_bool(cls, v):
        if isinstance(v, bool):
            raise ValueError("booleans are not numbers")
        return v

    def normalised(self) -> tuple[float, str]:
        return normalise(self.value, self.unit)


class Evidence(Strict):
    id: str
    title: str
    publisher: str
    url: str
    tier: SourceTier
    kind: SourceKind
    published: date
    retrieved_at: datetime
    as_of: date                       # the date the information describes
    excerpt: str
    datapoints: list[DataPoint] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    root_source: Optional[str] = None  # independence key; defaults to id
    derived_from: list[str] = Field(default_factory=list)
    supersedes: Optional[str] = None
    synthetic: bool = False
    flags: list[str] = Field(default_factory=list)

    @property
    def root(self) -> str:
        return self.root_source or self.id

    def content_hash(self) -> str:
        d = self.model_dump(mode="json", exclude={"flags", "retrieved_at"})
        return stable_hash(d)


# --------------------------------------------------------------------------- #
# Claims, assumptions, scenarios
# --------------------------------------------------------------------------- #
class Claim(Strict):
    id: str
    author: str
    text: str
    epistemic: Epistemic
    citations: list[str] = Field(default_factory=list)
    metric: Optional[str] = None
    value: Optional[float] = None
    unit: Optional[str] = None
    period: Optional[str] = None

    @property
    def quantitative(self) -> bool:
        return self.value is not None


class Verdict(str, Enum):
    SUPPORTED = "supported"
    UNKNOWN_CITATION = "unknown_citation"
    NO_CITATION = "no_citation"
    STALE_SOURCE = "stale_source"
    SUPERSEDED_SOURCE = "superseded_source"
    FUTURE_SOURCE = "future_source"            # look-ahead relative to session date
    NO_MATCHING_DATAPOINT = "no_matching_datapoint"
    VALUE_MISMATCH = "value_mismatch"
    UNIT_MISMATCH = "unit_mismatch"
    BASIS_MISMATCH = "basis_mismatch"          # e.g. guidance presented as fact
    CONTESTED = "contested"                    # conflicting sources unresolved
    CIRCULAR = "circular"
    FLAGGED_SOURCE = "flagged_source"          # cites evidence flagged for possible prompt injection
    QUALITATIVE_UNVERIFIED = "qualitative_unverified"
    UNSTRUCTURED_NUMBER = "unstructured_number"
    NOT_APPLICABLE = "not_applicable"          # assumptions/speculation: nothing to verify


BLOCKING_VERDICTS = {
    Verdict.UNKNOWN_CITATION, Verdict.VALUE_MISMATCH, Verdict.UNIT_MISMATCH,
    Verdict.FUTURE_SOURCE, Verdict.CIRCULAR, Verdict.SUPERSEDED_SOURCE, Verdict.FLAGGED_SOURCE,
}


class ClaimCheck(Strict):
    claim_id: str
    verdict: Verdict
    detail: str = ""
    supporting_evidence: list[str] = Field(default_factory=list)
    independent_roots: int = 0
    secondary_verdicts: list[Verdict] = Field(default_factory=list)


class Assumption(Strict):
    driver: str
    value: float
    epistemic: Epistemic
    basis_claims: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    rationale: str = ""
    proposed_by: str = "system"

    @field_validator("value", mode="before")
    @classmethod
    def _no_bool(cls, v):
        if isinstance(v, bool):
            raise ValueError("booleans are not numbers")
        return v


class GateFinding(Strict):
    driver: str
    scenario: str
    severity: Literal["error", "warning"]
    code: str
    detail: str


class Trigger(Strict):
    description: str
    metric: str
    operator: Literal["<", "<=", ">", ">="]
    threshold: float
    unit: str = ""


# --------------------------------------------------------------------------- #
# Valuation results
# --------------------------------------------------------------------------- #
class YearRow(Strict):
    year: int
    contracted_mw: float
    energized_mw: float
    gpus: float
    new_gpus: float
    retired_gpus: float
    revenue: float
    power_cost: float
    lease_cost: float
    other_opex: float
    ebitda: float
    depreciation: float
    writeoffs: float
    ebit: float
    tax: float
    capex: float
    delta_nwc: float
    fcff: float
    discount_factor: float
    pv_fcff: float


class BridgeResult(Strict):
    enterprise_value: float
    plus_cash: float
    less_debt: float
    less_leases: float
    less_preferred: float
    less_minority: float
    equity_value: float
    basic_shares: float
    diluted_shares: float
    value_per_share: float
    value_per_share_floored: float
    dilution_iterations: int
    lease_treatment: str


class ValuationResult(Strict):
    scenario: str
    analyst: str
    input_hash: str
    rows: list[YearRow]
    terminal_value: float
    pv_terminal: float
    terminal_share_of_ev: float
    implied_terminal_ev_ebitda: float
    bridge: BridgeResult
    diagnostics: dict[str, float] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    output_hash: str = ""

    @model_validator(mode="after")
    def _hash(self):
        if not self.output_hash:
            d = self.model_dump(mode="json", exclude={"output_hash"})
            self.output_hash = stable_hash(d)
        return self


class CreditRow(Strict):
    year: int
    debt_start: float
    new_debt: float
    maturities_refinanced: float
    interest: float
    ebitda: float
    net_debt_to_ebitda: float
    interest_coverage: float
    funding_gap: float  # positive = equity or other financing required


class CreditResult(Strict):
    rows: list[CreditRow]
    min_interest_coverage: float
    max_net_debt_to_ebitda: float
    cumulative_funding_gap: float
    refinancing_at_new_rate: float


class UnitEconomics(Strict):
    capex_per_gpu: float
    annual_contribution_y1: float
    cohort_irr: Optional[float]
    cohort_npv_at_wacc: float
    payback_years: Optional[float]


# --------------------------------------------------------------------------- #
# Analyst reports and debate
# --------------------------------------------------------------------------- #
class ScenarioSpec(Strict):
    name: Literal["bear", "base", "bull"]
    probability: float = Field(ge=0, le=1)
    assumptions: dict[str, Assumption]                                   # accepted; bear/bull hold overrides only
    rejected: dict[str, Assumption] = Field(default_factory=dict)        # proposals the gate refused (audit only)


class AnalystReport(Strict):
    role: str
    version: int
    thesis: str
    stance: Literal["positive", "neutral", "negative"]
    key_points: list[str]
    claims: list[Claim]
    claim_checks: list[ClaimCheck]
    scenarios: list[ScenarioSpec]
    gate_findings: list[GateFinding]
    valuations: dict[str, Optional[ValuationResult]]
    unvaluable_reasons: dict[str, list[str]] = Field(default_factory=dict)
    uncertainties: list[str]
    invalidation_triggers: list[Trigger]
    evidence_seen: list[str]
    model: str

    def scenario(self, name: str) -> Optional[ScenarioSpec]:
        return next((s for s in self.scenarios if s.name == name), None)

    def value(self, name: str) -> Optional[float]:
        v = self.valuations.get(name)
        return v.bridge.value_per_share_floored if v else None

    def expected_value(self) -> Optional[float]:
        total, w = 0.0, 0.0
        for s in self.scenarios:
            v = self.value(s.name)
            if v is None:
                return None
            total += s.probability * v
            w += s.probability
        return total / w if w else None


class DriverEffect(Strict):
    analyst: str
    value: float
    effect_per_share: float


class Disagreement(Strict):
    driver: str
    reference_value: float
    spread_per_share: float
    effects: list[DriverEffect]
    low_analyst: str
    high_analyst: str
    kind: Literal["interpretation", "information_asymmetry", "assumption"] = "assumption"
    note: str = ""


class AttributionResult(Strict):
    reference_value_per_share: float
    disagreements: list[Disagreement]
    interaction_residuals: dict[str, float]
    analyst_values: dict[str, float]


class ChallengeRecord(Strict):
    id: str
    from_role: str
    to_role: str
    driver: str
    question: str
    counter_value: Optional[float] = None
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_check: list[str] = Field(default_factory=list)  # ids that failed lookup
    response: str = ""
    concedes: Optional[bool] = None
    response_evidence_ids: list[str] = Field(default_factory=list)


class AssumptionChange(Strict):
    scenario: str
    driver: str
    old_value: Optional[float]
    new_value: float
    reason: str
    basis_challenge_ids: list[str]
    basis_evidence_ids: list[str]
    flags: list[str] = Field(default_factory=list)
    accepted: bool = True


class RevisionRecord(Strict):
    role: str
    changes: list[AssumptionChange]
    retained_view_reason: Optional[str]
    value_before: Optional[float]
    value_after: Optional[float]
    expected_before: Optional[float]
    expected_after: Optional[float]


class RuleResult(Strict):
    rule: str
    metric: str
    observed: Optional[float]
    threshold: float
    passed: bool
    action: Literal["veto", "cap_size", "warn"]
    detail: str = ""


class RiskReview(Strict):
    rule_results: list[RuleResult]
    veto: bool
    size_cap_fraction: Optional[float]
    probability_of_impairment: Optional[float]
    model_dispersion: Optional[float]
    narrative: str
    additional_risks: list[str]


class Recommendation(str, Enum):
    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"
    ABSTAIN = "abstain"


class Dissent(Strict):
    role: str
    expected_value_per_share: Optional[float]
    implied_view: Recommendation
    thesis: str


class Decision(Strict):
    recommendation: Recommendation
    rule_based_recommendation: Recommendation
    chair_override: bool
    override_justification: Optional[str]
    valuation_low: Optional[float]
    valuation_base: Optional[float]
    valuation_high: Optional[float]
    market_price: Optional[float]
    price_as_of: Optional[date]
    expected_return: Optional[float]
    position_size_fraction: Optional[float]
    position_size_basis: str
    primary_thesis: str
    strongest_opposing_thesis: str
    catalysts: list[str]
    key_risks: list[str]
    unresolved_questions: list[str]
    reconsideration_triggers: list[Trigger]
    dissents: list[Dissent]
    lint_flags: list[str]
    reasons: list[str]
