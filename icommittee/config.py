"""Configuration via environment variables and a YAML risk policy.

Nothing here has a hidden default model name: live runs must name their
models explicitly, so stale defaults can't silently change behaviour.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional

import yaml

ANALYST_ROLES = ["value", "growth", "credit", "industry", "contrarian"]
ALL_ROLES = ANALYST_ROLES + ["risk_manager", "chair"]


@dataclass
class Settings:
    session_date: date
    provider_default: str = "fixture"           # "fixture" | "openai:<model>" | "anthropic:<model>"
    role_models: dict[str, str] = field(default_factory=dict)
    cache_dir: Path = Path(".cache/llm")
    timeout_s: float = 90.0
    max_retries: int = 4
    temperature: float = 0.2
    blind_stage1: bool = True                   # analysts don't see the price in stage 1
    diverse_views: bool = True                  # role-specific secondary evidence
    max_disagreements: int = 3
    materiality_pct: float = 0.05               # driver spread / |reference value|
    materiality_abs: float = 0.50               # $/share floor
    numeric_tolerance: float = 0.01             # relative
    strict_gate: bool = False                   # True: reject (not downgrade) unsupported labels
    cost_per_mtok: dict[str, tuple[float, float]] = field(default_factory=dict)

    def model_for(self, role: str) -> str:
        return self.role_models.get(role, self.provider_default)

    @classmethod
    def from_env(cls, session_date: Optional[date] = None) -> "Settings":
        sd = session_date or date.fromisoformat(os.getenv("ICOMMITTEE_SESSION_DATE", date.today().isoformat()))
        s = cls(session_date=sd)
        s.provider_default = os.getenv("ICOMMITTEE_MODEL", "fixture")
        for role in ALL_ROLES:
            v = os.getenv(f"ICOMMITTEE_MODEL_{role.upper()}")
            if v:
                s.role_models[role] = v
        s.cache_dir = Path(os.getenv("ICOMMITTEE_CACHE_DIR", ".cache/llm"))
        s.timeout_s = float(os.getenv("ICOMMITTEE_TIMEOUT_S", s.timeout_s))
        s.max_retries = int(os.getenv("ICOMMITTEE_MAX_RETRIES", s.max_retries))
        s.temperature = float(os.getenv("ICOMMITTEE_TEMPERATURE", s.temperature))
        s.blind_stage1 = os.getenv("ICOMMITTEE_BLIND_STAGE1", "1") != "0"
        s.diverse_views = os.getenv("ICOMMITTEE_DIVERSE_VIEWS", "1") != "0"
        s.strict_gate = os.getenv("ICOMMITTEE_STRICT_GATE", "0") == "1"
        # Optional pricing table "model=in:out,model2=in:out" in USD per million tokens.
        for item in filter(None, os.getenv("ICOMMITTEE_PRICING", "").split(",")):
            name, prices = item.split("=")
            i, o = prices.split(":")
            s.cost_per_mtok[name.strip()] = (float(i), float(o))
        return s


# Freshness limits by source kind (days between as_of and session date).
DEFAULT_MAX_AGE_DAYS = {
    "market_data": 5,
    "sec_filing": 200,
    "earnings_release": 200,
    "investor_presentation": 365,
    "transcript": 200,
    "industry_research": 540,
    "news": 365,
    "macro": 120,
    "other": 365,
}


@dataclass
class RiskPolicy:
    max_net_debt_to_ebitda: float = 6.0          # peak, base case, any analyst median
    min_interest_coverage: float = 1.5
    max_bear_drawdown: float = 0.60              # bear value vs price
    max_prob_impairment: float = 0.35            # P(value < price*(1-impairment_threshold))
    impairment_threshold: float = 0.30
    max_model_dispersion: float = 0.75           # (p90-p10)/median across analysts' base cases
    max_terminal_share: float = 0.85
    max_position: float = 0.05                   # of NAV
    loss_budget: float = 0.01                    # max NAV loss in bear case
    hurdle_return: float = 0.15
    veto_rules: list[str] = field(default_factory=lambda: [
        "min_interest_coverage", "max_prob_impairment"])

    @classmethod
    def load(cls, path: Optional[Path]) -> "RiskPolicy":
        if not path:
            return cls()
        data = yaml.safe_load(Path(path).read_text()) or {}
        unknown = set(data) - set(cls.__dataclass_fields__)
        if unknown:
            raise ValueError(f"unknown risk policy keys: {sorted(unknown)}")
        return cls(**data)
