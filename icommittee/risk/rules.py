"""Deterministic risk rules and the committee's pooled valuation distribution.

The risk manager LLM writes commentary; it cannot create or remove a veto.
"""
from __future__ import annotations

import statistics
from typing import Optional

from ..config import RiskPolicy
from ..schemas import AnalystReport, CreditResult, Recommendation, RuleResult


def pooled_distribution(reports: list[AnalystReport]) -> list[tuple[float, float]]:
    """(value, weight) points. Each fully valued analyst gets equal weight,
    split across scenarios by that analyst's own probabilities.

    Equal weighting is a placeholder: analysts using the same base model are not
    independent, so this is not a calibrated probability distribution."""
    full = [r for r in reports if all(r.value(n) is not None for n in ("bear", "base", "bull"))]
    pts = []
    for r in full:
        for s in r.scenarios:
            pts.append((r.value(s.name), s.probability / len(full)))
    return pts


def weighted_quantile(points: list[tuple[float, float]], q: float) -> Optional[float]:
    if not points:
        return None
    pts = sorted(points)
    total = sum(w for _, w in pts)
    acc = 0.0
    for v, w in pts:
        acc += w
        if acc >= q * total - 1e-12:
            return v
    return pts[-1][0]


def weighted_mean(points: list[tuple[float, float]]) -> Optional[float]:
    total = sum(w for _, w in points)
    return sum(v * w for v, w in points) / total if total else None


def evaluate(reports: list[AnalystReport], price: Optional[float], credit: Optional[CreditResult],
             policy: RiskPolicy) -> dict:
    pts = pooled_distribution(reports)
    bases = [r.value("base") for r in reports if r.value("base") is not None]
    bears = [r.value("bear") for r in reports if r.value("bear") is not None]
    tshares = [r.valuations["base"].terminal_share_of_ev for r in reports
               if r.valuations.get("base") and r.valuations["base"].terminal_share_of_ev == r.valuations["base"].terminal_share_of_ev]
    med_base = statistics.median(bases) if bases else None
    dispersion = None
    if len(bases) >= 3 and med_base:
        qs = statistics.quantiles(bases, n=10, method="inclusive")
        dispersion = (qs[-1] - qs[0]) / abs(med_base)
    p_imp = None
    if price and pts:
        cut = price * (1 - policy.impairment_threshold)
        p_imp = sum(w for v, w in pts if v < cut) / sum(w for _, w in pts)
    bear_dd = None
    if price and bears:
        bear_dd = 1 - statistics.median(bears) / price

    def rule(name, metric, observed, threshold, ok, action, detail=""):
        return RuleResult(rule=name, metric=metric, observed=observed, threshold=threshold,
                          passed=ok, action=action, detail=detail)

    act = lambda name, default: "veto" if name in policy.veto_rules else default
    res = []
    if credit is not None:
        res.append(rule("min_interest_coverage", "EBITDA / interest, worst year (median-assumption case)",
                        credit.min_interest_coverage, policy.min_interest_coverage,
                        credit.min_interest_coverage >= policy.min_interest_coverage,
                        act("min_interest_coverage", "warn")))
        res.append(rule("max_net_debt_to_ebitda", "peak net debt / EBITDA (median-assumption case)",
                        credit.max_net_debt_to_ebitda, policy.max_net_debt_to_ebitda,
                        credit.max_net_debt_to_ebitda <= policy.max_net_debt_to_ebitda,
                        act("max_net_debt_to_ebitda", "warn")))
    else:
        res.append(rule("min_interest_coverage", "credit projection unavailable", None,
                        policy.min_interest_coverage, False, act("min_interest_coverage", "warn"),
                        "no complete median-assumption case; cannot verify coverage"))
    res.append(rule("max_prob_impairment", f"P(value < price x {1 - policy.impairment_threshold:.2f})",
                    p_imp, policy.max_prob_impairment,
                    p_imp is not None and p_imp <= policy.max_prob_impairment,
                    act("max_prob_impairment", "warn"),
                    "" if p_imp is not None else "needs a market price and fully valued reports"))
    res.append(rule("max_bear_drawdown", "1 - median bear value / price", bear_dd, policy.max_bear_drawdown,
                    bear_dd is not None and bear_dd <= policy.max_bear_drawdown,
                    act("max_bear_drawdown", "cap_size")))
    res.append(rule("max_model_dispersion", "(p90 - p10) / median of analysts' base values", dispersion,
                    policy.max_model_dispersion,
                    dispersion is not None and dispersion <= policy.max_model_dispersion,
                    act("max_model_dispersion", "warn")))
    if tshares:
        mt = statistics.median(tshares)
        res.append(rule("max_terminal_share", "median terminal value share of EV", mt, policy.max_terminal_share,
                        mt <= policy.max_terminal_share, act("max_terminal_share", "warn")))
    veto = any(r.action == "veto" and not r.passed for r in res)
    size = None
    if price and bear_dd is not None and not veto:
        loss = max(bear_dd, 0.05)
        size = min(policy.max_position, policy.loss_budget / loss)
    return {"rule_results": res, "veto": veto, "size_cap_fraction": 0.0 if veto else size,
            "probability_of_impairment": p_imp, "model_dispersion": dispersion, "pooled": pts,
            "median_base": med_base}


def implied_view(expected: Optional[float], price: Optional[float], hurdle: float) -> Recommendation:
    if expected is None or not price:
        return Recommendation.ABSTAIN
    er = expected / price - 1
    if er > hurdle:
        return Recommendation.BUY
    if er < -hurdle:
        return Recommendation.SELL
    return Recommendation.HOLD
