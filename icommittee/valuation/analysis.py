"""Sensitivity tables, reverse DCF, and disagreement attribution."""
from __future__ import annotations

import statistics
from typing import Optional

from ..schemas import AttributionResult, Disagreement, DriverEffect
from .drivers import DRIVERS, FORECAST_DRIVERS
from .model import ValuationConsistencyError, value


def per_share(x: dict[str, float], lease_treatment: str = "opex", floored: bool = True) -> float:
    b = value(x, lease_treatment=lease_treatment).bridge
    return b.value_per_share_floored if floored else b.value_per_share


def sensitivity(x: dict[str, float], d1: str, v1: list[float], d2: str, v2: list[float]
                ) -> list[list[Optional[float]]]:
    grid = []
    for a in v1:
        row = []
        for b in v2:
            y = dict(x, **{d1: a, d2: b})
            try:
                row.append(per_share(y))
            except ValuationConsistencyError:
                row.append(None)
        grid.append(row)
    return grid


def reverse_solve(x: dict[str, float], driver: str, target: float, iters: int = 80
                  ) -> Optional[float]:
    """Value of `driver` (others fixed) at which value per share equals `target`.
    Returns None if the target is unreachable within the driver's plausibility bounds."""
    spec = DRIVERS[driver]
    lo, hi = spec.lo, spec.hi
    if driver == "terminal_growth":
        hi = min(hi, x["wacc"] - 0.0101)
    if driver == "wacc":
        lo = max(lo, x["terminal_growth"] + 0.0101)
    f = lambda v: per_share(dict(x, **{driver: v})) - target
    try:
        flo, fhi = f(lo), f(hi)
    except ValuationConsistencyError:
        return None
    if flo * fhi > 0:
        return None
    for _ in range(iters):
        mid = (lo + hi) / 2
        fm = f(mid)
        if flo * fm <= 0:
            hi = mid
        else:
            lo, flo = mid, fm
    return (lo + hi) / 2


def attribute(analyst_inputs: dict[str, dict[str, float]], max_items: int = 3,
              materiality_pct: float = 0.05, materiality_abs: float = 0.5
              ) -> AttributionResult:
    """One-at-a-time attribution against a median reference.

    For each analyst and each forecast driver, swap the analyst's value into the
    committee-median input set and measure the change in value per share. A
    driver's spread is (max effect - min effect) across analysts. The residual
    (total gap - sum of single-driver effects) measures interactions this method
    cannot assign; it is reported, not hidden.
    """
    roles = sorted(analyst_inputs)
    ref = dict(next(iter(analyst_inputs.values())))
    for d in FORECAST_DRIVERS:
        ref[d] = statistics.median(analyst_inputs[r][d] for r in roles)
    # Unfloored values: the zero floor on equity would hide driver effects below zero.
    ps = lambda x: per_share(x, floored=False)
    ref_v = ps(ref)
    values = {r: ps(analyst_inputs[r]) for r in roles}
    effects: dict[str, list[DriverEffect]] = {d: [] for d in FORECAST_DRIVERS}
    residual = {}
    for r in roles:
        total = 0.0
        for d in FORECAST_DRIVERS:
            if analyst_inputs[r][d] == ref[d]:
                e = 0.0
            else:
                try:
                    e = ps(dict(ref, **{d: analyst_inputs[r][d]})) - ref_v
                except ValuationConsistencyError:
                    e = 0.0
            effects[d].append(DriverEffect(analyst=r, value=analyst_inputs[r][d], effect_per_share=e))
            total += e
        residual[r] = (values[r] - ref_v) - total
    threshold = max(materiality_abs, materiality_pct * abs(ref_v))
    dis = []
    for d, es in effects.items():
        # Ties (several analysts at the reference value) go to the analyst whose overall
        # valuation is most extreme in that direction, so the pairing is a real opposing view.
        lo = min(es, key=lambda e: (e.effect_per_share, values[e.analyst]))
        hi = max(es, key=lambda e: (e.effect_per_share, values[e.analyst]))
        spread = hi.effect_per_share - lo.effect_per_share
        if spread >= threshold and lo.analyst != hi.analyst:
            dis.append(Disagreement(driver=d, reference_value=ref[d], spread_per_share=spread,
                                    effects=es, low_analyst=lo.analyst, high_analyst=hi.analyst))
    dis.sort(key=lambda z: -z.spread_per_share)
    return AttributionResult(reference_value_per_share=ref_v, disagreements=dis[:max_items],
                             interaction_residuals=residual, analyst_values=values)
