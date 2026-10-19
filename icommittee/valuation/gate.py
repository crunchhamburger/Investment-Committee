"""The assumption gate: the only door into the valuation model.

Facts come from the registry. Forecasts come from analysts, and each one is
checked for: known driver, plausibility bounds, honest epistemic label, and
basis claims that actually verified. Nothing is defaulted: a missing input
makes the scenario unvaluable, and the report says why.
"""
from __future__ import annotations

from typing import Optional

from ..evidence.registry import EvidenceRegistry, UnresolvedConflict
from ..schemas import (BLOCKING_VERDICTS, Assumption, Claim, ClaimCheck, Epistemic, GateFinding,
                       ScenarioSpec, Verdict, normalise)
from .drivers import DRIVERS, FACT_DRIVERS, FORECAST_DRIVERS, UNIT_FAMILY_OF_DRIVER

_SOURCED_LABELS = {Epistemic.MANAGEMENT_GUIDANCE, Epistemic.THIRD_PARTY_ESTIMATE}
_OK = {Verdict.SUPPORTED, Verdict.STALE_SOURCE}


class FactLayer:
    """Starting-position facts shared by every analyst."""

    def __init__(self, facts: dict[str, Assumption], missing: dict[str, str]):
        self.facts = facts
        self.missing = missing

    @classmethod
    def from_registry(cls, reg: EvidenceRegistry) -> "FactLayer":
        facts, missing = {}, {}
        for name in FACT_DRIVERS:
            spec = DRIVERS[name]
            try:
                hit = reg.best_fact(spec.fact_metric)
            except UnresolvedConflict as e:
                missing[name] = f"conflict: {e}"
                continue
            if hit is None:
                missing[name] = f"no primary verified datapoint for metric '{spec.fact_metric}'"
                continue
            ev, dp = hit
            val, fam = dp.normalised()
            if fam != UNIT_FAMILY_OF_DRIVER[spec.unit]:
                missing[name] = f"unit family {fam} incompatible with {spec.unit}"
                continue
            stale = reg.status(ev.id) == "stale"
            facts[name] = Assumption(driver=name, value=val, epistemic=Epistemic.VERIFIED_FACT,
                                     evidence_ids=[ev.id], proposed_by="fact_layer",
                                     rationale=f"{ev.publisher}: {dp.metric} {dp.period}"
                                               + (" (STALE)" if stale else ""))
        return cls(facts, missing)

    def values(self) -> dict[str, float]:
        return {k: a.value for k, a in self.facts.items()}


def gate_assumption(a: Assumption, scenario: str, facts: FactLayer,
                    claims: dict[str, Claim], checks: dict[str, ClaimCheck],
                    strict: bool = False, tol: float = 0.01
                    ) -> tuple[Optional[Assumption], list[GateFinding]]:
    f: list[GateFinding] = []
    err = lambda code, msg: f.append(GateFinding(driver=a.driver, scenario=scenario, severity="error",
                                                 code=code, detail=msg))
    warn = lambda code, msg: f.append(GateFinding(driver=a.driver, scenario=scenario,
                                                  severity="error" if strict else "warning",
                                                  code=code, detail=msg))
    spec = DRIVERS.get(a.driver)
    if spec is None:
        err("unknown_driver", f"{a.driver} is not a model driver")
        return None, f
    if spec.kind == "fact":
        fact = facts.facts.get(a.driver)
        if fact is None:
            err("fact_override", "facts come only from the evidence registry; this fact is missing there")
        elif abs(fact.value - a.value) > tol * max(abs(fact.value), 1e-9):
            err("fact_override", f"analyst proposed {a.value:,.4g} but registry fact is {fact.value:,.4g}")
        return None, f
    if not (spec.lo <= a.value <= spec.hi):
        err("out_of_bounds", f"{a.value} outside [{spec.lo}, {spec.hi}] {spec.unit}")
        return None, f
    if a.epistemic == Epistemic.SPECULATION:
        err("speculation_in_model", "speculation cannot enter the valuation; restate as an owned assumption")
        return None, f
    if a.epistemic == Epistemic.MODEL_DERIVED:
        err("model_derived_input", "model outputs cannot be fed back as inputs")
        return None, f

    basis = [(claims.get(c), checks.get(c)) for c in a.basis_claims]
    if any(cl is None for cl, _ in basis):
        err("unknown_basis_claim", f"unknown basis claims {[c for c in a.basis_claims if c not in claims]}")
        return None, f
    failed = [cl.id for cl, ck in basis if ck and ck.verdict in BLOCKING_VERDICTS]
    if failed:
        err("basis_contradicted", f"basis claims failed verification: "
                                  f"{[(c, checks[c].verdict.value) for c in failed]}")
        return None, f

    out = a.model_copy()
    if a.epistemic == Epistemic.VERIFIED_FACT:
        warn("forecast_labelled_fact", "a forecast cannot be a verified fact; relabelled analyst_assumption")
        out.epistemic = Epistemic.ANALYST_ASSUMPTION
    elif a.epistemic in _SOURCED_LABELS:
        fam = UNIT_FAMILY_OF_DRIVER[spec.unit]
        support = []
        for cl, ck in basis:
            if ck and ck.verdict in _OK and cl.epistemic == a.epistemic and cl.value is not None:
                v, cfam = normalise(cl.value, cl.unit)
                if cfam == fam:
                    support.append((cl, v))
        if not support:
            warn("unsupported_label", f"labelled {a.epistemic.value} without a verified basis claim of that "
                                      "type; relabelled analyst_assumption")
            out.epistemic = Epistemic.ANALYST_ASSUMPTION
        elif not any(abs(v - a.value) <= tol * max(abs(v), 1e-9) for _, v in support):
            warn("value_differs_from_source", f"value {a.value:,.4g} differs from cited "
                                              f"{[round(v, 6) for _, v in support]}; relabelled analyst_assumption")
            out.epistemic = Epistemic.ANALYST_ASSUMPTION
    if out.epistemic == Epistemic.ANALYST_ASSUMPTION and len(out.rationale.strip()) < 15:
        err("no_rationale", "analyst assumptions must state a rationale")
        return None, f
    if strict and any(x.severity == "error" for x in f):
        return None, f
    return out, f


def assemble_scenarios(specs: list[ScenarioSpec], facts: FactLayer, claims: dict[str, Claim],
                       checks: dict[str, ClaimCheck], strict: bool = False
                       ):
    """Gate every assumption; bear/bull inherit base for drivers they don't override.

    Returns (merged inputs per scenario or None, findings, unvaluable reasons,
    accepted own-assumptions per scenario, rejected raw proposals per scenario).
    Previously rejected proposals are re-gated, so a fixed basis claim can clear them,
    and an unfixed one keeps the scenario unvaluable across report versions."""
    findings: list[GateFinding] = []
    accepted: dict[str, dict[str, Assumption]] = {}
    rejected_raw: dict[str, dict[str, Assumption]] = {}
    rejected: dict[str, list[str]] = {}
    for s in specs:
        acc, rej = {}, {}
        proposals = dict(s.rejected)
        proposals.update(s.assumptions)
        for a in proposals.values():
            ok, f = gate_assumption(a, s.name, facts, claims, checks, strict)
            findings.extend(f)
            if ok is not None:
                acc[a.driver] = ok
            elif DRIVERS.get(a.driver) is None or DRIVERS[a.driver].kind == "forecast":
                rejected.setdefault(s.name, []).append(a.driver)
                rej[a.driver] = a
        accepted[s.name] = acc
        rejected_raw[s.name] = rej
    base = accepted.get("base", {})
    out: dict[str, Optional[dict[str, Assumption]]] = {}
    reasons: dict[str, list[str]] = {}
    for s in specs:
        merged = dict(facts.facts)
        merged.update(base)
        merged.update(accepted[s.name])
        missing = [k for k in FACT_DRIVERS + FORECAST_DRIVERS if k not in merged]
        if s.name != "base" and rejected.get(s.name):
            # Never fall back to the base value for an override the gate rejected:
            # the analyst meant a different number, and silently using base would misstate the case.
            out[s.name] = None
            reasons[s.name] = [f"{d}: override rejected by gate (see findings); scenario not valued"
                               for d in rejected[s.name]]
        elif missing:
            out[s.name] = None
            reasons[s.name] = [f"{k}: {facts.missing.get(k, 'not provided or rejected by gate')}"
                               for k in missing]
        else:
            out[s.name] = merged
    return out, findings, reasons, accepted, rejected_raw
