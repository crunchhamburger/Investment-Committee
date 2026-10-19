"""Versioned, append-only evidence registry.

Revisions are new records that `supersede` older ones; nothing is edited in
place, so every past valuation can be reproduced from the registry snapshot
it was computed against.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable, Optional

from ..config import DEFAULT_MAX_AGE_DAYS
from ..schemas import DataPoint, Epistemic, Evidence, SourceTier, stable_hash
from .sanitize import injection_findings


class RegistryError(Exception):
    pass


class UnresolvedConflict(RegistryError):
    pass


@dataclass
class Conflict:
    metric: str
    period: str
    values: list[tuple[str, float, str]]  # (evidence id, normalised value, tier)
    resolved_by: Optional[str]           # evidence id chosen, or None if unresolved
    reason: str


class EvidenceRegistry:
    def __init__(self, session_date: date, path: Optional[Path] = None,
                 tolerance: float = 0.005, max_age_days: Optional[dict] = None):
        self.session_date = session_date
        self.path = Path(path) if path else None
        self.tolerance = tolerance
        self.max_age = dict(DEFAULT_MAX_AGE_DAYS, **(max_age_days or {}))
        self._items: dict[str, Evidence] = {}
        self._order: list[str] = []
        self.events: list[dict] = []

    # ---------------- persistence ----------------
    def add(self, ev: Evidence) -> Evidence:
        if ev.id in self._items:
            if self._items[ev.id].content_hash() == ev.content_hash():
                return self._items[ev.id]
            raise RegistryError(
                f"evidence {ev.id} already exists with different content; "
                "add a new record with `supersedes` instead of editing")
        if ev.supersedes and ev.supersedes not in self._items:
            raise RegistryError(f"{ev.id} supersedes unknown evidence {ev.supersedes}")
        for parent in ev.derived_from:
            if parent not in self._items:
                raise RegistryError(f"{ev.id} derived_from unknown evidence {parent}")
        hits = injection_findings(ev.excerpt + " " + ev.title)
        if hits:
            ev = ev.model_copy(update={"flags": sorted(set(ev.flags) | {"possible_injection"})})
        self._items[ev.id] = ev
        self._order.append(ev.id)
        self.events.append({"event": "evidence_added", "id": ev.id, "hash": ev.content_hash(),
                            "injection_hits": hits})
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a") as f:
                f.write(ev.model_dump_json() + "\n")
        return ev

    def extend(self, items: Iterable[Evidence]) -> None:
        for ev in items:
            self.add(ev)

    @classmethod
    def load(cls, path: Path, session_date: date, **kw) -> "EvidenceRegistry":
        reg = cls(session_date, path=None, **kw)
        for line in Path(path).read_text().splitlines():
            if line.strip():
                reg.add(Evidence.model_validate_json(line))
        reg.path = Path(path)
        return reg

    # ---------------- lookup & status ----------------
    def __contains__(self, eid: str) -> bool:
        return eid in self._items

    def get(self, eid: str) -> Optional[Evidence]:
        return self._items.get(eid)

    def all(self) -> list[Evidence]:
        return [self._items[i] for i in self._order]

    def superseded_ids(self) -> set[str]:
        return {e.supersedes for e in self._items.values() if e.supersedes}

    def status(self, eid: str) -> str:
        """active | superseded | stale | future | unknown"""
        ev = self._items.get(eid)
        if ev is None:
            return "unknown"
        if ev.published > self.session_date:
            return "future"
        if eid in self.superseded_ids():
            return "superseded"
        limit = self.max_age.get(ev.kind.value, 365)
        if (self.session_date - ev.as_of).days > limit:
            return "stale"
        return "active"

    def visible(self) -> list[Evidence]:
        """Evidence an agent may see: published on or before session date, not superseded."""
        return [e for e in self.all() if self.status(e.id) in ("active", "stale")]

    def roots(self, eids: Iterable[str]) -> set[str]:
        """Independent origins of a set of evidence ids (follows derived_from)."""
        out: set[str] = set()
        seen: set[str] = set()
        stack = list(eids)
        while stack:
            eid = stack.pop()
            if eid in seen:
                continue
            seen.add(eid)
            ev = self._items.get(eid)
            if ev is None:
                continue
            if ev.derived_from:
                stack.extend(ev.derived_from)
            else:
                out.add(ev.root)
        return out

    # ---------------- conflicts & facts ----------------
    def conflicts(self) -> list[Conflict]:
        groups: dict[tuple[str, str], list[tuple[Evidence, DataPoint]]] = {}
        for ev in self.all():
            if self.status(ev.id) not in ("active", "stale"):
                continue
            for dp in ev.datapoints:
                if dp.basis == Epistemic.VERIFIED_FACT:
                    groups.setdefault((dp.metric, dp.period), []).append((ev, dp))
        out = []
        for (metric, period), items in groups.items():
            vals = [(ev.id, dp.normalised()[0], ev.tier.value) for ev, dp in items]
            ref = vals[0][1]
            if all(_close(v, ref, self.tolerance) for _, v, _ in vals):
                continue
            primaries = [x for x in vals if x[2] == SourceTier.PRIMARY.value]
            if primaries and all(_close(v, primaries[0][1], self.tolerance) for _, v, _ in primaries):
                latest = max(primaries, key=lambda x: self._items[x[0]].published)
                out.append(Conflict(metric, period, vals, latest[0],
                                    "primary source(s) agree; secondary disagreement overruled"))
            else:
                out.append(Conflict(metric, period, vals, None,
                                    "primary sources disagree or no primary source; needs human review"))
        return out

    def best_fact(self, metric: str, period: Optional[str] = None
                  ) -> Optional[tuple[Evidence, DataPoint]]:
        """Latest active primary verified fact for a metric (optionally a period)."""
        unresolved = {(c.metric, c.period) for c in self.conflicts() if c.resolved_by is None}
        cands = []
        for ev in self.all():
            if ev.tier != SourceTier.PRIMARY or self.status(ev.id) not in ("active", "stale"):
                continue
            for dp in ev.datapoints:
                if dp.metric == metric and dp.basis == Epistemic.VERIFIED_FACT and (
                        period is None or dp.period == period):
                    if (dp.metric, dp.period) in unresolved:
                        raise UnresolvedConflict(f"{metric} {dp.period}: conflicting primary sources")
                    cands.append((ev, dp))
        if not cands:
            return None
        return max(cands, key=lambda x: (x[0].as_of, x[0].published))

    def snapshot_hash(self) -> str:
        return stable_hash([self._items[i].content_hash() for i in self._order])


def _close(a: float, b: float, tol: float) -> bool:
    if a == b:
        return True
    return abs(a - b) <= tol * max(abs(a), abs(b), 1e-12)
