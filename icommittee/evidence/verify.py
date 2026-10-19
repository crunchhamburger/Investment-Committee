"""Claim verification: does the cited evidence actually support the claim?

A citation ID existing is the weakest possible check. This module checks:
  * the evidence exists, was published before the session date, and is not superseded
  * the claim's support isn't circular (the committee citing its own output)
  * quantitative claims match a structured datapoint (metric, period, unit, value)
  * the source's epistemic basis matches the claim's (guidance is not fact)
  * "verified facts" rest on at least one primary source
  * numbers written in prose but not in structured fields are flagged
  * how many *independent* origins support the claim

Qualitative support (does this paragraph entail this sentence?) cannot be
checked deterministically. It is delegated to an optional SupportJudge and
otherwise reported as unverified rather than passed.
"""
from __future__ import annotations

import re
from typing import Optional, Protocol

from ..schemas import (Claim, ClaimCheck, Epistemic, SourceTier, UNIT_FAMILY, Verdict,
                       normalise)
from .registry import EvidenceRegistry

_SOURCED = {Epistemic.VERIFIED_FACT, Epistemic.MANAGEMENT_GUIDANCE, Epistemic.THIRD_PARTY_ESTIMATE}

_NUM = re.compile(
    r"(?<![A-Za-z\d.])\$?(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?\s*"
    r"(%|percent|bn|billion|b\b|mn|million|m\b|k\b|thousand|x\b|MW|GW|kW)?",
    re.IGNORECASE)
_SUFFIX = {"%": 0.01, "percent": 0.01, "bn": 1e9, "billion": 1e9, "b": 1e9, "mn": 1e6,
           "million": 1e6, "m": 1e6, "k": 1e3, "thousand": 1e3, "gw": 1e3}
_STOP = set("the a an of to in and or for on by with is are was were be as at from that this its it "
            "their our has have had will would could than which into over per".split())


class SupportJudge(Protocol):
    def judge(self, claim_text: str, excerpts: dict[str, str]) -> tuple[bool, str]: ...


def numbers_in_text(text: str) -> list[float]:
    out = []
    for m in _NUM.finditer(text):
        whole, frac, suf = m.group(1), m.group(2) or "", (m.group(3) or "").lower()
        raw = float(whole.replace(",", "") + frac)
        # Skip bare years and quarter/period labels like "FY2025", "Q2".
        if not suf and not frac and 1900 <= raw <= 2100 and "," not in whole:
            continue
        start = m.start()
        if start > 0 and text[start - 1] in "QqHh":
            continue
        out.append(raw * _SUFFIX.get(suf, 1.0))
    return out


def _matches_any(target: float, candidates: list[float], tol: float) -> bool:
    for c in candidates:
        for scale in (1, 1e3, 1e6, 1e9, 1e-2, 1e2):
            v = c * scale
            if abs(v - target) <= tol * max(abs(target), 1e-12) + 1e-12:
                return True
    return False


class ClaimVerifier:
    def __init__(self, registry: EvidenceRegistry, tolerance: float = 0.01,
                 judge: Optional[SupportJudge] = None):
        self.reg = registry
        self.tol = tolerance
        self.judge = judge
        self._conflicts = None

    def _conflict_index(self):
        if self._conflicts is None:
            self._conflicts = {(c.metric, c.period): c for c in self.reg.conflicts()}
        return self._conflicts

    def check(self, claim: Claim) -> ClaimCheck:
        cid = claim.id
        secondary: list[Verdict] = []

        if not claim.citations:
            if claim.epistemic in _SOURCED:
                return ClaimCheck(claim_id=cid, verdict=Verdict.NO_CITATION,
                                  detail=f"{claim.epistemic.value} requires a citation")
            return ClaimCheck(claim_id=cid, verdict=Verdict.NOT_APPLICABLE,
                              detail=f"{claim.epistemic.value}: no external support claimed")

        unknown = [e for e in claim.citations if e not in self.reg]
        if unknown:
            return ClaimCheck(claim_id=cid, verdict=Verdict.UNKNOWN_CITATION,
                              detail=f"unknown evidence ids: {unknown}")

        statuses = {e: self.reg.status(e) for e in claim.citations}
        future = [e for e, s in statuses.items() if s == "future"]
        if future:
            return ClaimCheck(claim_id=cid, verdict=Verdict.FUTURE_SOURCE,
                              detail=f"published after session date (look-ahead): {future}")
        superseded = [e for e, s in statuses.items() if s == "superseded"]
        if superseded:
            newer = [x.id for x in self.reg.all() if x.supersedes in superseded]
            return ClaimCheck(claim_id=cid, verdict=Verdict.SUPERSEDED_SOURCE,
                              detail=f"{superseded} superseded by {newer}")

        flagged = [e for e in claim.citations if "possible_injection" in self.reg.get(e).flags]
        if flagged:
            return ClaimCheck(claim_id=cid, verdict=Verdict.FLAGGED_SOURCE,
                              detail=f"cites evidence flagged for instruction-like content: {flagged}; "
                                     "needs human review before it can support a number")

        roots = self.reg.roots(claim.citations)
        if roots and all(r.startswith("committee:") for r in roots):
            return ClaimCheck(claim_id=cid, verdict=Verdict.CIRCULAR,
                              detail="all support traces back to committee-generated material",
                              independent_roots=0)
        independent = len({r for r in roots if not r.startswith("committee:")})
        if all(s == "stale" for s in statuses.values()):
            secondary.append(Verdict.STALE_SOURCE)

        evs = [self.reg.get(e) for e in claim.citations]

        # ---------- quantitative claims ----------
        if claim.quantitative:
            if not (claim.metric and claim.unit and claim.period):
                return ClaimCheck(claim_id=cid, verdict=Verdict.NO_MATCHING_DATAPOINT,
                                  detail="quantitative claim must state metric, unit and period")
            if claim.unit not in UNIT_FAMILY:
                return ClaimCheck(claim_id=cid, verdict=Verdict.UNIT_MISMATCH,
                                  detail=f"unknown unit {claim.unit}")
            cval, cfam = normalise(claim.value, claim.unit)
            text_nums = numbers_in_text(claim.text)
            if text_nums and not _matches_any(cval, text_nums, self.tol):
                secondary.append(Verdict.UNSTRUCTURED_NUMBER)

            matches = [(ev, dp) for ev in evs for dp in ev.datapoints
                       if dp.metric == claim.metric and dp.period == claim.period]
            if not matches:
                return ClaimCheck(claim_id=cid, verdict=Verdict.NO_MATCHING_DATAPOINT,
                                  detail=f"no {claim.metric} for {claim.period} in {claim.citations}",
                                  independent_roots=independent, secondary_verdicts=secondary)
            fam_ok = [(ev, dp) for ev, dp in matches if dp.normalised()[1] == cfam]
            if not fam_ok:
                return ClaimCheck(claim_id=cid, verdict=Verdict.UNIT_MISMATCH,
                                  detail=f"claim unit family {cfam} vs source "
                                         f"{[dp.unit for _, dp in matches]}")
            agree = [(ev, dp) for ev, dp in fam_ok
                     if abs(dp.normalised()[0] - cval) <= self.tol * max(abs(cval), 1e-12)]
            conflict = self._conflict_index().get((claim.metric, claim.period))
            if conflict and conflict.resolved_by is None:
                return ClaimCheck(claim_id=cid, verdict=Verdict.CONTESTED,
                                  detail=f"unresolved conflict: {conflict.values}",
                                  independent_roots=independent)
            if conflict and conflict.resolved_by:
                winner = next(v for i, v, _ in conflict.values if i == conflict.resolved_by)
                if abs(winner - cval) > self.tol * max(abs(cval), 1e-12):
                    return ClaimCheck(claim_id=cid, verdict=Verdict.VALUE_MISMATCH,
                                      detail=f"claimed {cval:,.4g} but primary source "
                                             f"{conflict.resolved_by} reports {winner:,.4g}",
                                      independent_roots=independent)
            if not agree:
                src = ", ".join(f"{ev.id}={dp.normalised()[0]:,.4g}" for ev, dp in fam_ok)
                return ClaimCheck(claim_id=cid, verdict=Verdict.VALUE_MISMATCH,
                                  detail=f"claimed {cval:,.4g}; sources say {src}",
                                  independent_roots=independent, secondary_verdicts=secondary)
            if claim.epistemic in _SOURCED and all(dp.basis != claim.epistemic for _, dp in agree):
                return ClaimCheck(claim_id=cid, verdict=Verdict.BASIS_MISMATCH,
                                  detail=f"claim labelled {claim.epistemic.value} but source labels it "
                                         f"{sorted({dp.basis.value for _, dp in agree})}",
                                  supporting_evidence=[ev.id for ev, _ in agree],
                                  independent_roots=independent)
            if claim.epistemic == Epistemic.VERIFIED_FACT and not any(
                    ev.tier == SourceTier.PRIMARY for ev, _ in agree):
                return ClaimCheck(claim_id=cid, verdict=Verdict.BASIS_MISMATCH,
                                  detail="verified facts need at least one primary source",
                                  supporting_evidence=[ev.id for ev, _ in agree],
                                  independent_roots=independent)
            verdict = Verdict.STALE_SOURCE if Verdict.STALE_SOURCE in secondary else Verdict.SUPPORTED
            return ClaimCheck(claim_id=cid, verdict=verdict,
                              detail="matched structured datapoint",
                              supporting_evidence=[ev.id for ev, _ in agree],
                              independent_roots=len(self.reg.roots([ev.id for ev, _ in agree])),
                              secondary_verdicts=[v for v in secondary if v != Verdict.STALE_SOURCE])

        # ---------- qualitative claims ----------
        if claim.epistemic in _SOURCED and numbers_in_text(claim.text):
            return ClaimCheck(claim_id=cid, verdict=Verdict.UNSTRUCTURED_NUMBER,
                              detail="claim states a number in prose without structured metric/value; "
                                     "restate it as a quantitative claim so it can be checked",
                              independent_roots=independent)
        excerpts = {ev.id: ev.excerpt for ev in evs}
        overlap = _overlap(claim.text, " ".join(excerpts.values()))
        if self.judge is not None:
            ok, why = self.judge.judge(claim.text, excerpts)
            return ClaimCheck(claim_id=cid,
                              verdict=Verdict.SUPPORTED if ok else Verdict.QUALITATIVE_UNVERIFIED,
                              detail=f"judge: {why} (lexical overlap {overlap:.2f})",
                              supporting_evidence=list(excerpts) if ok else [],
                              independent_roots=independent, secondary_verdicts=secondary)
        return ClaimCheck(claim_id=cid, verdict=Verdict.QUALITATIVE_UNVERIFIED,
                          detail=f"no support judge configured; lexical overlap {overlap:.2f}",
                          independent_roots=independent, secondary_verdicts=secondary)

    def check_all(self, claims: list[Claim]) -> list[ClaimCheck]:
        return [self.check(c) for c in claims]


def _overlap(claim: str, source: str) -> float:
    words = lambda s: {w for w in re.findall(r"[a-z]{3,}", s.lower()) if w not in _STOP}
    c, s = words(claim), words(source)
    return len(c & s) / len(c) if c else 0.0
