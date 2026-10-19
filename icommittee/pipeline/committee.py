"""Six-stage committee pipeline.

LLM calls (bounded): 5 initial reports, <=5 challenge sets, <=5 response sets,
5 revisions, 1 risk narrative, 1 chair narrative. Everything that decides a
number (verification, gating, valuation, disagreement ranking, conformity
detection, risk rules, valuation range, rule-based recommendation) is code.
"""
from __future__ import annotations

import re
import statistics
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from ..agents import prompts
from ..agents.outputs import (AnalystDraft, ChairDraft, ChallengeSet, LLMAssumption, LLMClaim,
                              ResponseSet, RevisionProposal, RiskCommentary)
from ..agents.roles import CHAIR, RISK_MANAGER, ROLES
from ..config import ANALYST_ROLES, RiskPolicy, Settings
from ..evidence.registry import EvidenceRegistry
from ..evidence.verify import ClaimVerifier
from ..llm.client import PermanentError, StructuredLLM
from ..risk import rules as risk_rules
from ..schemas import (AnalystReport, Assumption, AssumptionChange, AttributionResult, ChallengeRecord,
                       Claim, Decision, Dissent, Evidence, Recommendation, RevisionRecord,
                       RiskReview, ScenarioSpec, SourceKind, SourceTier, stable_hash)
from ..valuation import analysis
from ..valuation.drivers import FORECAST_DRIVERS
from ..valuation.gate import FactLayer, assemble_scenarios, gate_assumption
from ..valuation.model import ValuationConsistencyError, credit_projection, unit_economics, value

_CONSENSUS_RX = re.compile(
    r"\b(consensus|unanimous|all (five |the )?analysts|majority of (the )?analysts|"
    r"(most|several|many|\d) (of the )?analysts (agree|concur|support|believe))", re.IGNORECASE)


@dataclass
class SessionResult:
    company: str
    session_date: date
    registry_hash: str
    synthetic: bool
    facts: dict
    facts_missing: dict
    reports_v1: dict[str, AnalystReport]
    attribution: Optional[AttributionResult]
    challenges: list[ChallengeRecord]
    revisions: dict[str, RevisionRecord]
    reports_v2: dict[str, AnalystReport]
    risk: RiskReview
    decision: Decision
    diagnostics: dict
    llm: dict
    events: list[dict] = field(default_factory=list)

    def to_json(self) -> dict:
        dump = lambda m: m.model_dump(mode="json") if m is not None else None
        return {
            "company": self.company, "session_date": str(self.session_date),
            "registry_hash": self.registry_hash, "synthetic": self.synthetic,
            "facts": self.facts, "facts_missing": self.facts_missing,
            "reports_v1": {k: dump(v) for k, v in self.reports_v1.items()},
            "attribution": dump(self.attribution),
            "challenges": [dump(c) for c in self.challenges],
            "revisions": {k: dump(v) for k, v in self.revisions.items()},
            "reports_v2": {k: dump(v) for k, v in self.reports_v2.items()},
            "risk": dump(self.risk), "decision": dump(self.decision),
            "diagnostics": self.diagnostics, "llm": self.llm, "events": self.events,
        }

    def decision_fingerprint(self) -> str:
        d = self.decision
        return stable_hash({"rec": d.recommendation.value, "low": _r(d.valuation_low),
                            "base": _r(d.valuation_base), "high": _r(d.valuation_high),
                            "veto": self.risk.veto})


def _r(x):
    return None if x is None else round(x, 4)


class Committee:
    def __init__(self, registry: EvidenceRegistry, llm: StructuredLLM, settings: Settings,
                 policy: Optional[RiskPolicy] = None, company: str = "", verifier: Optional[ClaimVerifier] = None):
        self.reg = registry
        self.llm = llm
        self.s = settings
        self.policy = policy or RiskPolicy()
        self.company = company
        self.verifier = verifier or ClaimVerifier(registry, tolerance=settings.numeric_tolerance)
        self.facts = FactLayer.from_registry(registry)
        self.events: list[dict] = []

    # ------------------------------------------------------------------ helpers
    def log(self, event: str, **kw):
        self.events.append({"event": event, **kw})

    def view_for(self, role: str) -> list[Evidence]:
        topics = set(ROLES[role].evidence_topics) if role in ROLES else set()
        out = []
        for e in self.reg.visible():
            if self.s.blind_stage1 and e.kind == SourceKind.MARKET_DATA:
                continue
            if e.tier == SourceTier.PRIMARY or not self.s.diverse_views or not topics:
                out.append(e)
            elif topics & set(e.topics) or not e.topics:
                out.append(e)
        return out

    def market_price(self) -> tuple[Optional[float], Optional[date], Optional[str]]:
        hit = self.reg.best_fact("share_price")
        if hit is None:
            return None, None, "no verified share price in registry"
        ev, dp = hit
        status = self.reg.status(ev.id)
        note = f"{ev.publisher}, as of {ev.as_of}" + (" - STALE" if status == "stale" else "")
        return dp.value, ev.as_of, note

    def _claims(self, role: str, raw: list[LLMClaim]) -> list[Claim]:
        return [Claim(id=f"{role}.{c.id}", author=role, text=c.text, epistemic=c.epistemic,
                      citations=c.citations, metric=c.metric, value=c.value, unit=c.unit, period=c.period)
                for c in raw]

    @staticmethod
    def _assumption(role: str, a: LLMAssumption) -> Assumption:
        return Assumption(driver=a.driver, value=a.value, epistemic=a.epistemic,
                          basis_claims=[f"{role}.{c}" if "." not in c else c for c in a.basis_claims],
                          rationale=a.rationale, proposed_by=role)

    def build_report(self, role: str, version: int, *, thesis: str, stance: str, key_points: list[str],
                     claims: list[Claim], scenarios: list[ScenarioSpec], uncertainties: list[str],
                     triggers, evidence_seen: list[str]) -> AnalystReport:
        checks = self.verifier.check_all(claims)
        cmap = {c.id: c for c in claims}
        kmap = {k.claim_id: k for k in checks}
        assembled, findings, reasons, accepted, rejected = assemble_scenarios(
            scenarios, self.facts, cmap, kmap, self.s.strict_gate)
        vals = {}
        for name, inputs in assembled.items():
            if inputs is None:
                vals[name] = None
                continue
            try:
                vals[name] = value({k: a.value for k, a in inputs.items()}, analyst=role, scenario=name)
            except ValuationConsistencyError as e:
                vals[name] = None
                reasons[name] = [str(e)]
        for s in scenarios:
            # Store only this scenario's own accepted assumptions; merging with base and facts
            # happens at valuation time, so a revised base driver flows into bear/bull.
            s.assumptions = accepted[s.name]
            s.rejected = rejected[s.name]
        rep = AnalystReport(role=role, version=version, thesis=thesis, stance=stance, key_points=key_points,
                            claims=claims, claim_checks=checks, scenarios=scenarios, gate_findings=findings,
                            valuations=vals, unvaluable_reasons=reasons, uncertainties=uncertainties,
                            invalidation_triggers=list(triggers), evidence_seen=evidence_seen,
                            model=self.s.model_for(role))
        self.log("report_built", role=role, version=version,
                 values={n: rep.value(n) for n in ("bear", "base", "bull")},
                 rejected=[f.model_dump() for f in findings if f.severity == "error"],
                 claim_verdicts={k.claim_id: k.verdict.value for k in checks})
        return rep

    # ------------------------------------------------------------------ stage 1
    def stage1(self) -> dict[str, AnalystReport]:
        out = {}
        for role in ANALYST_ROLES:
            ev = self.view_for(role)
            user = prompts.stage1_user(ROLES[role], self.company, ev, self.facts, None)
            try:
                d = self.llm.call(role=role, stage="stage1", system=prompts.system_prompt(ROLES[role]),
                                  user=user, schema=AnalystDraft)
            except PermanentError as e:
                self.log("analyst_failed", role=role, stage="stage1", error=str(e))
                continue
            claims = self._claims(role, d.claims)
            specs = [ScenarioSpec(name=s.name, probability=s.probability,
                                  assumptions={a.driver: self._assumption(role, a) for a in s.assumptions})
                     for s in d.scenarios]
            out[role] = self.build_report(role, 1, thesis=d.thesis, stance=d.stance, key_points=d.key_points,
                                          claims=claims, scenarios=specs, uncertainties=d.uncertainties,
                                          triggers=d.invalidation_triggers, evidence_seen=[e.id for e in ev])
        return out

    # ------------------------------------------------------------------ stage 2
    def stage2(self, reports: dict[str, AnalystReport]) -> Optional[AttributionResult]:
        inputs = {}
        for role, r in reports.items():
            if r.valuations.get("base") is None:
                continue
            base = r.scenario("base")
            x = self.facts.values()
            x.update({k: a.value for k, a in base.assumptions.items()})
            inputs[role] = x
        if len(inputs) < 2:
            self.log("attribution_skipped", reason="fewer than two valued base cases")
            return None
        res = analysis.attribute(inputs, self.s.max_disagreements, self.s.materiality_pct, self.s.materiality_abs)
        for d in res.disagreements:
            lo, hi = reports[d.low_analyst], reports[d.high_analyst]
            cites = lambda r: {e for a in [r.scenario("base").assumptions.get(d.driver)] if a
                               for c in a.basis_claims for cl in r.claims if cl.id == c for e in cl.citations}
            clo, chi = cites(lo), cites(hi)
            if (clo - set(hi.evidence_seen)) or (chi - set(lo.evidence_seen)):
                d.kind = "information_asymmetry"
                d.note = "one side cites evidence the other side did not see"
            elif clo & chi:
                d.kind = "interpretation"
                d.note = "both sides cite the same evidence for different values"
        self.log("disagreements", items=[(d.driver, round(d.spread_per_share, 3), d.kind) for d in res.disagreements])
        return res

    # ------------------------------------------------------------------ stage 3
    def stage3(self, reports: dict[str, AnalystReport], attr: Optional[AttributionResult]) -> list[ChallengeRecord]:
        if attr is None:
            return []
        assignments: dict[str, list[tuple[str, str]]] = {}
        for d in attr.disagreements:
            assignments.setdefault(d.low_analyst, []).append((d.high_analyst, d.driver))
            assignments.setdefault(d.high_analyst, []).append((d.low_analyst, d.driver))
        records: dict[str, ChallengeRecord] = {}
        for challenger, pairs in sorted(assignments.items()):
            me = reports[challenger]
            user = prompts.challenge_user(me, [(reports[t], d) for t, d in pairs], self.view_for(challenger))
            try:
                cs = self.llm.call(role=challenger, stage="challenge", system=prompts.system_prompt(ROLES[challenger]),
                                   user=user, schema=ChallengeSet)
            except PermanentError as e:
                self.log("challenge_failed", role=challenger, error=str(e))
                continue
            allowed = set(pairs)
            for c in cs.challenges:
                key = (c.target_role, c.driver)
                cid = f"{challenger}->{c.target_role}:{c.driver}"
                if key not in allowed or cid in records:
                    self.log("challenge_dropped", id=cid, reason="not an assigned disagreement or duplicate")
                    continue
                records[cid] = ChallengeRecord(id=cid, from_role=challenger, to_role=c.target_role, driver=c.driver,
                                               question=c.question, counter_value=c.counter_value,
                                               evidence_ids=c.evidence_ids,
                                               evidence_check=[e for e in c.evidence_ids if e not in self.reg])
        by_target: dict[str, list[ChallengeRecord]] = {}
        for c in records.values():
            by_target.setdefault(c.to_role, []).append(c)
        for target, cs in sorted(by_target.items()):
            try:
                rs = self.llm.call(role=target, stage="respond", system=prompts.system_prompt(ROLES[target]),
                                   user=prompts.response_user(reports[target], cs), schema=ResponseSet)
            except PermanentError as e:
                self.log("response_failed", role=target, error=str(e))
                continue
            for r in rs.responses:
                if r.challenge_id in records and records[r.challenge_id].to_role == target:
                    rec = records[r.challenge_id]
                    rec.response, rec.concedes, rec.response_evidence_ids = r.response, r.concedes, r.evidence_ids
        return list(records.values())

    # ------------------------------------------------------------------ stage 4
    def stage4(self, reports: dict[str, AnalystReport], challenges: list[ChallengeRecord],
               attr: Optional[AttributionResult]) -> tuple[dict[str, AnalystReport], dict[str, RevisionRecord]]:
        median = {}
        if attr:
            for d in FORECAST_DRIVERS:
                vals = [r.scenario("base").assumptions[d].value for r in reports.values()
                        if r.scenario("base") and d in r.scenario("base").assumptions]
                if vals:
                    median[d] = statistics.median(vals)
        new_reports, revisions = {}, {}
        for role, r in reports.items():
            involving = [c for c in challenges if role in (c.from_role, c.to_role)]
            try:
                p = self.llm.call(role=role, stage="revise", system=prompts.system_prompt(ROLES[role]),
                                  user=prompts.revision_user(r, involving), schema=RevisionProposal)
            except PermanentError as e:
                self.log("revision_failed", role=role, error=str(e))
                new_reports[role] = r
                continue
            new_claims = r.claims + self._claims(role, p.new_claims)
            new_checks = {k.claim_id: k for k in self.verifier.check_all(new_claims)}
            cmap = {c.id: c for c in new_claims}
            prior_cited = {e for c in r.claims for e in c.citations}
            valid_challenges = {c.id for c in involving}
            specs = [s.model_copy(deep=True) for s in r.scenarios]
            if p.scenario_probabilities:
                for s in specs:
                    s.probability = p.scenario_probabilities[s.name]
            changes = []
            for ch in p.changes:
                spec = next(s for s in specs if s.name == ch.scenario)
                old = spec.assumptions.get(ch.driver)
                if old is None and ch.scenario != "base":
                    base_a = next(s for s in specs if s.name == "base").assumptions.get(ch.driver)
                    old_v = base_a.value if base_a else None
                else:
                    old_v = old.value if old else None
                flags = []
                bad_ch = [c for c in ch.basis_challenge_ids if c not in valid_challenges]
                bad_ev = [e for e in ch.basis_evidence_ids if e not in self.reg]
                if bad_ch:
                    flags.append(f"unknown_challenge:{bad_ch}")
                if bad_ev:
                    flags.append(f"unknown_evidence:{bad_ev}")
                good_ch = [c for c in ch.basis_challenge_ids if c in valid_challenges]
                good_ev = [e for e in ch.basis_evidence_ids if e in self.reg]
                accepted = True
                if not good_ch and not good_ev and not ch.basis_claims:
                    flags.append("no_basis")
                    accepted = False
                new_info = (set(good_ev) - prior_cited) | {e for c in challenges if c.id in good_ch
                                                           for e in c.evidence_ids + c.response_evidence_ids
                                                           if e in self.reg and e not in prior_cited}
                if (accepted and ch.scenario == "base" and old_v is not None and ch.driver in median
                        and abs(ch.new_value - median[ch.driver]) < abs(old_v - median[ch.driver])
                        and not new_info):
                    flags.append("conformity_suspect: moved toward committee median without new evidence")
                a = Assumption(driver=ch.driver, value=ch.new_value, epistemic=ch.epistemic,
                               basis_claims=[f"{role}.{c}" if "." not in c else c for c in ch.basis_claims],
                               evidence_ids=good_ev, rationale=ch.reason, proposed_by=role)
                if accepted:
                    ok, f = gate_assumption(a, ch.scenario, self.facts, cmap, new_checks, self.s.strict_gate)
                    if ok is None:
                        accepted = False
                        flags.extend(f"gate:{x.code}" for x in f)
                    else:
                        spec.assumptions[ch.driver] = ok
                        spec.rejected.pop(ch.driver, None)
                changes.append(AssumptionChange(scenario=ch.scenario, driver=ch.driver, old_value=old_v,
                                                new_value=ch.new_value, reason=ch.reason,
                                                basis_challenge_ids=ch.basis_challenge_ids,
                                                basis_evidence_ids=ch.basis_evidence_ids, flags=flags,
                                                accepted=accepted))
            v2 = self.build_report(role, 2, thesis=r.thesis, stance=r.stance, key_points=r.key_points,
                                   claims=new_claims, scenarios=specs, uncertainties=r.uncertainties,
                                   triggers=r.invalidation_triggers, evidence_seen=r.evidence_seen)
            new_reports[role] = v2
            revisions[role] = RevisionRecord(role=role, changes=changes, retained_view_reason=p.retained_view_reason,
                                             value_before=r.value("base"), value_after=v2.value("base"),
                                             expected_before=r.expected_value(), expected_after=v2.expected_value())
        return new_reports, revisions

    # ------------------------------------------------------------------ stage 5
    def median_inputs(self, reports: dict[str, AnalystReport]) -> Optional[dict[str, float]]:
        bases = [r.scenario("base") for r in reports.values() if r.valuations.get("base")]
        if not bases or self.facts.missing:
            return None
        x = self.facts.values()
        for d in FORECAST_DRIVERS:
            x[d] = statistics.median(b.assumptions[d].value for b in bases)
        return x

    def stage5(self, reports: dict[str, AnalystReport], price: Optional[float]) -> tuple[RiskReview, dict]:
        mx = self.median_inputs(reports)
        credit = credit_projection(mx) if mx else None
        ev = risk_rules.evaluate(list(reports.values()), price, credit, self.policy)
        ue = unit_economics(mx) if mx else None
        summary = {"rules": [r.model_dump() for r in ev["rule_results"]], "veto": ev["veto"],
                   "probability_of_impairment": ev["probability_of_impairment"],
                   "model_dispersion": ev["model_dispersion"],
                   "credit": credit.model_dump() if credit else None,
                   "unit_economics": ue.model_dump() if ue else None}
        try:
            c = self.llm.call(role="risk_manager", stage="risk", system=prompts.system_prompt(RISK_MANAGER),
                              user=prompts.risk_user(summary), schema=RiskCommentary)
            narrative, extra = c.narrative, c.additional_risks
        except PermanentError as e:
            narrative, extra = f"(risk narrative unavailable: {e})", []
        review = RiskReview(rule_results=ev["rule_results"], veto=ev["veto"], size_cap_fraction=ev["size_cap_fraction"],
                            probability_of_impairment=ev["probability_of_impairment"],
                            model_dispersion=ev["model_dispersion"], narrative=narrative, additional_risks=extra)
        return review, {"pooled": ev["pooled"], "median_inputs": mx, "credit": credit, "unit_economics": ue}

    # ------------------------------------------------------------------ stage 6
    def stage6(self, reports: dict[str, AnalystReport], risk: RiskReview, pooled, price, price_date, price_note,
               attr, revisions, extra) -> Decision:
        reasons = []
        low = risk_rules.weighted_quantile(pooled, 0.10)
        high = risk_rules.weighted_quantile(pooled, 0.90)
        mean = risk_rules.weighted_mean(pooled)
        er = (mean / price - 1) if (mean is not None and price) else None
        stale_price = price_note is not None and "STALE" in price_note
        full = [r for r in reports.values() if r.expected_value() is not None]
        if price is None:
            rule_rec = Recommendation.ABSTAIN
            reasons.append("no verified market price")
        elif stale_price:
            rule_rec = Recommendation.ABSTAIN
            reasons.append(f"market price is stale ({price_note})")
        elif len(full) < 3:
            rule_rec = Recommendation.ABSTAIN
            reasons.append(f"only {len(full)} analysts produced fully valued reports (need 3)")
        elif risk.model_dispersion is not None and risk.model_dispersion > self.policy.max_model_dispersion:
            rule_rec = Recommendation.ABSTAIN
            reasons.append(f"analyst base-case dispersion {risk.model_dispersion:.0%} exceeds "
                           f"{self.policy.max_model_dispersion:.0%}: the committee cannot form a view")
        else:
            rule_rec = risk_rules.implied_view(mean, price, self.policy.hurdle_return)
            reasons.append(f"probability-weighted value {mean:.2f} vs price {price:.2f} "
                           f"(expected return {er:+.1%}, hurdle {self.policy.hurdle_return:.0%})")
            if risk.veto and rule_rec == Recommendation.BUY:
                rule_rec = Recommendation.HOLD
                reasons.append("risk veto blocks BUY: " + ", ".join(
                    r.rule for r in risk.rule_results if r.action == "veto" and not r.passed))
        summary = {
            "company": self.company, "price": price, "price_note": price_note,
            "valuation_range_p10_mean_p90": [low, mean, high], "expected_return": er,
            "rule_based_recommendation": rule_rec.value, "reasons": reasons,
            "analysts": {r.role: {"thesis": r.thesis, "stance": r.stance,
                                  "values": {n: r.value(n) for n in ("bear", "base", "bull")},
                                  "triggers": [t.model_dump() for t in r.invalidation_triggers]}
                         for r in reports.values()},
            "disagreements": [d.model_dump() for d in (attr.disagreements if attr else [])],
            "revisions": {k: v.model_dump() for k, v in revisions.items()},
            "risk": risk.model_dump(),
            "reverse_dcf": extra.get("reverse"),
        }
        lint = []
        try:
            c = self.llm.call(role="chair", stage="chair", system=prompts.system_prompt(CHAIR),
                              user=prompts.chair_user(summary), schema=ChairDraft)
        except PermanentError as e:
            c = ChairDraft(primary_thesis=f"(chair narrative unavailable: {e})", strongest_opposing_thesis="",
                           catalysts=[], key_risks=[], unresolved_questions=[],
                           reconsideration_triggers=[t for r in reports.values() for t in r.invalidation_triggers][:3]
                           or [{"description": "n/a", "metric": "n/a", "operator": "<", "threshold": 0}])
            lint.append("chair_unavailable")
        text = " ".join([c.primary_thesis, c.strongest_opposing_thesis] + c.key_risks + c.catalysts)
        if _CONSENSUS_RX.search(text):
            lint.append("consensus_cited_as_support: analyst agreement is not independent evidence")
        unknown = [e for e in c.cited_evidence if e not in self.reg]
        if unknown:
            lint.append(f"chair_cites_unknown_evidence:{unknown}")
        if not c.cited_evidence:
            lint.append("chair_thesis_uncited")
        if self.reg_synthetic():
            lint.append("synthetic_data: not investable")
        final, override, just = rule_rec, False, None
        if c.recommendation_override and c.recommendation_override != rule_rec:
            if not c.override_justification or len(c.override_justification) < 40:
                lint.append("override_rejected: no substantive justification")
            elif risk.veto and c.recommendation_override == Recommendation.BUY:
                lint.append("override_rejected: cannot override a risk veto")
            elif rule_rec == Recommendation.ABSTAIN and reasons and (price is None or stale_price):
                lint.append("override_rejected: cannot recommend without a current verified price")
            else:
                final, override, just = c.recommendation_override, True, c.override_justification
                lint.append(f"chair_override:{rule_rec.value}->{final.value}")
        dissents = []
        for r in reports.values():
            view = risk_rules.implied_view(r.expected_value(), price, self.policy.hurdle_return)
            if view != final:
                dissents.append(Dissent(role=r.role, expected_value_per_share=r.expected_value(),
                                        implied_view=view, thesis=r.thesis))
        if dissents and len(dissents) == len(reports) and final != Recommendation.ABSTAIN:
            lint.append("decision_held_by_no_analyst: the committee view is an average of positions nobody holds; "
                        "read the dissent table, not the headline")
        size = None if final != Recommendation.BUY else risk.size_cap_fraction
        return Decision(recommendation=final, rule_based_recommendation=rule_rec, chair_override=override,
                        override_justification=just, valuation_low=low, valuation_base=mean, valuation_high=high,
                        market_price=price, price_as_of=price_date, expected_return=er,
                        position_size_fraction=size,
                        position_size_basis=(f"min(max_position {self.policy.max_position:.0%}, loss_budget "
                                             f"{self.policy.loss_budget:.1%} / median bear drawdown); NAV-relative; "
                                             "ignores correlation with the rest of the portfolio"),
                        primary_thesis=c.primary_thesis, strongest_opposing_thesis=c.strongest_opposing_thesis,
                        catalysts=c.catalysts, key_risks=c.key_risks + risk.additional_risks,
                        unresolved_questions=c.unresolved_questions,
                        reconsideration_triggers=c.reconsideration_triggers, dissents=dissents,
                        lint_flags=lint, reasons=reasons)

    def reg_synthetic(self) -> bool:
        return any(e.synthetic for e in self.reg.visible())

    # ------------------------------------------------------------------ run
    def run(self) -> SessionResult:
        self.log("session_start", registry_hash=self.reg.snapshot_hash(), facts_missing=self.facts.missing,
                 conflicts=[(c.metric, c.period, c.resolved_by, c.reason) for c in self.reg.conflicts()])
        v1 = self.stage1()
        attr = self.stage2(v1)
        challenges = self.stage3(v1, attr)
        v2, revisions = self.stage4(v1, challenges, attr)
        price, price_date, price_note = self.market_price()
        risk, extra = self.stage5(v2, price)
        mx = extra["median_inputs"]
        reverse = {}
        if mx and price:
            for d in ("price_per_gpu_hour_new", "utilization", "capex_per_gpu", "wacc", "energization_rate"):
                reverse[d] = {"median_assumption": mx[d], "value_that_justifies_price": analysis.reverse_solve(mx, d, price)}
        extra["reverse"] = reverse
        decision = self.stage6(v2, risk, extra["pooled"], price, price_date, price_note, attr, revisions, extra)
        diagnostics = {
            "price_note": price_note,
            "reverse_dcf": reverse,
            "unit_economics": extra["unit_economics"].model_dump() if extra["unit_economics"] else None,
            "credit": extra["credit"].model_dump() if extra["credit"] else None,
            "sensitivity_price_x_utilization": None,
            "models_by_role": {r: self.s.model_for(r) for r in ANALYST_ROLES + ["risk_manager", "chair"]},
            "shared_model_warning": len({self.s.model_for(r) for r in ANALYST_ROLES}) == 1,
        }
        if mx:
            pv = [round(mx["price_per_gpu_hour_new"] * k, 3) for k in (0.7, 0.85, 1.0, 1.15, 1.3)]
            uv = [round(min(1.0, max(0.05, mx["utilization"] + d)), 3) for d in (-0.15, -0.075, 0, 0.075)]
            diagnostics["sensitivity_price_x_utilization"] = {
                "rows_utilization": uv, "cols_price": pv,
                "grid": analysis.sensitivity(mx, "utilization", uv, "price_per_gpu_hour_new", pv)}
        self.log("decision", recommendation=decision.recommendation.value, lint=decision.lint_flags)
        return SessionResult(company=self.company, session_date=self.s.session_date,
                             registry_hash=self.reg.snapshot_hash(), synthetic=self.reg_synthetic(),
                             facts=self.facts.values(), facts_missing=self.facts.missing,
                             reports_v1=v1, attribution=attr, challenges=challenges, revisions=revisions,
                             reports_v2=v2, risk=risk, decision=decision, diagnostics=diagnostics,
                             llm=self.llm.summary(), events=self.reg.events + self.events)
