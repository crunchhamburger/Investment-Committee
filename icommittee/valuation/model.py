"""Deterministic GPU-cloud operating model, DCF, EV-to-equity bridge,
credit projection and cohort unit economics.

Agents never run this code's arithmetic in their heads: they propose drivers,
this module computes. Every function is pure: same inputs -> same outputs.

Simplifications are deliberate and listed in docs/LIMITATIONS.md; the most
important: annual periods, end-of-year discounting, no NOL carryforwards,
constant WACC, power cost scales with utilisation, leases expensed in opex.
"""
from __future__ import annotations

import math
from typing import Optional

from ..schemas import (BridgeResult, CreditResult, CreditRow, UnitEconomics, ValuationResult,
                       YearRow, stable_hash)
from .drivers import DRIVERS

HOURS = 8760.0


class MissingInputError(ValueError):
    def __init__(self, missing: list[str]):
        super().__init__(f"missing required inputs: {missing}")
        self.missing = missing


class ValuationConsistencyError(ValueError):
    pass


def _require(inputs: dict[str, float]) -> None:
    missing = [k for k in DRIVERS if k not in inputs or inputs[k] is None]
    if missing:
        raise MissingInputError(missing)
    for k, v in inputs.items():
        if k not in DRIVERS:
            raise ValuationConsistencyError(f"unknown driver {k}")
        if isinstance(v, bool) or not isinstance(v, (int, float)) or math.isnan(v):
            raise ValuationConsistencyError(f"{k} must be a real number, got {v!r}")
        d = DRIVERS[k]
        if not (d.lo <= v <= d.hi):
            raise ValuationConsistencyError(f"{k}={v} outside plausibility bounds [{d.lo}, {d.hi}]")
    if inputs["wacc"] - inputs["terminal_growth"] < 0.01:
        raise ValuationConsistencyError("wacc must exceed terminal_growth by at least 1pp")
    if inputs["energized_power_mw_0"] > inputs["contracted_power_mw_0"] * 1.0001:
        raise ValuationConsistencyError("energised MW cannot exceed contracted MW")


def _gpus_for(mw: float, x: dict) -> float:
    return mw / x["pue"] * 1000.0 / x["kw_per_gpu"]


def operating_model(x: dict[str, float], horizon: int = 6) -> tuple[list[YearRow], dict]:
    _require(x)
    econ = int(round(x["gpu_economic_life_years"]))
    useful = int(round(x["gpu_useful_life_years"]))
    age0 = int(round(x["existing_fleet_avg_age"]))
    util, decay = x["utilization"], x["price_decay_per_year_of_age"]

    contracted, energized = x["contracted_power_mw_0"], x["energized_power_mw_0"]
    vintages: dict[int, float] = {}          # purchase year -> GPU count
    gpu0 = _gpus_for(energized, x)
    if gpu0 > 0:
        # Spread the installed fleet evenly over ages 0..2*avg_age so it doesn't all
        # retire in one year (a single-vintage fleet creates an artificial capex spike).
        ages = list(range(0, 2 * age0 + 1)) if age0 > 0 else [0]
        for a in ages:
            vintages[-a] = gpu0 / len(ages)
    capex_by_vintage: dict[int, float] = {}

    def price_new(t: int) -> float:
        return x["price_per_gpu_hour_new"] * (1 + x["price_new_growth_per_year"]) ** max(t - 1, 0)

    def revenue(t: int, required: float) -> float:
        fleet = sum(vintages.values())
        if fleet <= 0:
            return 0.0
        active = min(1.0, required / fleet)
        return sum(n * HOURS * util * price_new(t) * (1 - decay) ** max(t - v, 0)
                   for v, n in vintages.items()) * active

    prev_rev = revenue(0, gpu0)
    ppe0, ppe_life = x["existing_ppe_net_0"], int(round(x["existing_ppe_remaining_life"]))
    rows: list[YearRow] = []
    for t in range(1, horizon + 1):
        backlog = contracted - energized
        contracted += x["mw_additions_per_year"]
        energized += x["energization_rate"] * max(backlog, 0.0)
        required = _gpus_for(energized, x)

        retired, writeoffs = 0.0, 0.0
        for v in [v for v in vintages if t - v >= econ]:
            retired += vintages.pop(v)
            if v in capex_by_vintage and econ < useful:
                writeoffs += capex_by_vintage[v] * (1 - econ / useful)
        new = max(0.0, required - sum(vintages.values()))
        if new > 0:
            vintages[t] = vintages.get(t, 0.0) + new
        capex = new * x["capex_per_gpu"]
        if capex:
            capex_by_vintage[t] = capex

        rev = revenue(t, required)
        power = energized * HOURS * x["power_cost_per_mwh"] * util
        lease = energized * x["lease_cost_per_mw_year"]
        other = x["other_opex_pct_revenue"] * rev
        ebitda = rev - power - lease - other
        dep = (ppe0 / ppe_life if t <= ppe_life else 0.0)
        dep += sum(c / useful for v, c in capex_by_vintage.items() if v <= t < v + min(useful, econ))
        ebit = ebitda - dep - writeoffs
        tax = max(0.0, ebit) * x["tax_rate"]
        dnwc = x["nwc_pct_revenue_change"] * (rev - prev_rev)
        fcff = ebit - tax + dep + writeoffs - capex - dnwc
        df = 1.0 / (1 + x["wacc"]) ** t
        rows.append(YearRow(year=t, contracted_mw=contracted, energized_mw=energized, gpus=required,
                            new_gpus=new, retired_gpus=retired, revenue=rev, power_cost=power,
                            lease_cost=lease, other_opex=other, ebitda=ebitda, depreciation=dep,
                            writeoffs=writeoffs, ebit=ebit, tax=tax, capex=capex, delta_nwc=dnwc,
                            fcff=fcff, discount_factor=df, pv_fcff=fcff * df))
        prev_rev = rev

    # ---- normalised terminal year (steady-state reinvestment, not a growth-capex year) ----
    last = rows[-1]
    g = x["terminal_growth"]
    margin = last.ebitda / last.revenue if last.revenue else 0.0
    rev_t = last.revenue * (1 + g)
    ebitda_t = margin * rev_t
    maint = last.gpus * x["capex_per_gpu"] / econ
    dep_t = maint * (1 + g)
    capex_t = maint * (1 + g) + max(g, 0.0) * last.gpus * x["capex_per_gpu"]
    ebit_t = ebitda_t - dep_t
    tax_t = max(0.0, ebit_t) * x["tax_rate"]
    fcff_t = ebit_t - tax_t + dep_t - capex_t - x["nwc_pct_revenue_change"] * (rev_t - last.revenue)
    tv = fcff_t / (x["wacc"] - g)
    terminal = {"terminal_fcff": fcff_t, "terminal_value": tv, "pv_terminal": tv * last.discount_factor,
                "terminal_ebitda": ebitda_t, "maintenance_capex": maint}
    return rows, terminal


def equity_bridge(ev: float, x: dict[str, float], lease_treatment: str = "opex") -> BridgeResult:
    if lease_treatment not in ("opex", "debt"):
        raise ValuationConsistencyError("lease_treatment must be 'opex' or 'debt'")
    if lease_treatment == "debt" and x["lease_cost_per_mw_year"] > 0:
        raise ValuationConsistencyError(
            "double count: lease costs are deducted in the operating model AND lease liabilities "
            "would be subtracted in the bridge. Use lease_treatment='opex' or set lease cost to 0.")
    leases = x["lease_liabilities_0"] if lease_treatment == "debt" else 0.0
    equity = (ev + x["cash_0"] - x["gross_debt_0"] - leases
              - x["preferred_0"] - x["minority_interest_0"])
    basic = x["basic_shares_0"]
    base_shares = basic + x["rsus_0"]
    shares, it = base_shares, 0
    if equity > 0:
        # Treasury-stock method evaluated at the model's own value per share, not the
        # market price, so dilution does not anchor on the quote.
        p = equity / base_shares
        for it in range(1, 100):
            k = x["options_0"] * max(0.0, 1 - x["options_strike"] / p) if p > 0 else 0.0
            shares = base_shares + k
            p_new = equity / shares
            if abs(p_new - p) < 1e-10:
                break
            p = p_new
    vps = equity / shares
    return BridgeResult(enterprise_value=ev, plus_cash=x["cash_0"], less_debt=x["gross_debt_0"],
                        less_leases=leases, less_preferred=x["preferred_0"],
                        less_minority=x["minority_interest_0"], equity_value=equity,
                        basic_shares=basic, diluted_shares=shares, value_per_share=vps,
                        value_per_share_floored=max(0.0, vps), dilution_iterations=it,
                        lease_treatment=lease_treatment)


def value(x: dict[str, float], analyst: str = "", scenario: str = "", horizon: int = 6,
          lease_treatment: str = "opex") -> ValuationResult:
    rows, term = operating_model(x, horizon)
    ev = sum(r.pv_fcff for r in rows) + term["pv_terminal"]
    bridge = equity_bridge(ev, x, lease_treatment)
    last = rows[-1]
    tshare = term["pv_terminal"] / ev if ev > 0 else float("nan")
    warnings = []
    if ev <= 0:
        warnings.append("enterprise value is non-positive under these assumptions")
    if bridge.equity_value <= 0:
        warnings.append("equity value is non-positive: equity is out of the money; per-share value floored at 0")
    if ev > 0 and tshare > 0.85:
        warnings.append(f"terminal value is {tshare:.0%} of EV: valuation is mostly a perpetuity assumption")
    if x["gpu_useful_life_years"] > x["gpu_economic_life_years"]:
        warnings.append("accounting life exceeds economic life: reported EBIT overstates economics until write-offs hit")
    diagnostics = {
        "revenue_y1": rows[0].revenue,
        "revenue_final": last.revenue,
        "revenue_cagr": (last.revenue / rows[0].revenue) ** (1 / max(len(rows) - 1, 1)) - 1
        if rows[0].revenue > 0 and last.revenue > 0 else float("nan"),
        "ebitda_margin_final": last.ebitda / last.revenue if last.revenue else float("nan"),
        "revenue_per_energized_mw_y1": rows[0].revenue / rows[0].energized_mw if rows[0].energized_mw else float("nan"),
        "cumulative_capex": sum(r.capex for r in rows),
        "cumulative_fcff": sum(r.fcff for r in rows),
        "maintenance_capex_terminal": term["maintenance_capex"],
    }
    return ValuationResult(
        scenario=scenario, analyst=analyst, input_hash=stable_hash({k: x[k] for k in sorted(x)}),
        rows=rows, terminal_value=term["terminal_value"], pv_terminal=term["pv_terminal"],
        terminal_share_of_ev=tshare,
        implied_terminal_ev_ebitda=term["terminal_value"] / last.ebitda if last.ebitda > 0 else float("nan"),
        bridge=bridge, diagnostics=diagnostics, warnings=warnings)


def credit_projection(x: dict[str, float], horizon: int = 6) -> CreditResult:
    rows_op, _ = operating_model(x, horizon)
    old, new_bal = x["gross_debt_0"], 0.0
    cash = x["cash_0"]
    out: list[CreditRow] = []
    refi_total = 0.0
    cum_gap = 0.0
    for r in rows_op:
        start = old + new_bal
        maturity = x.get(f"debt_maturity_y{r.year}", 0.0) if r.year <= 3 else 0.0
        maturity = min(maturity, old)
        interest = old * x["avg_interest_rate_0"] + new_bal * x["new_debt_rate"]
        old -= maturity
        new_bal += maturity                    # refinanced at the new rate
        refi_total += maturity
        borrow = x["debt_funded_share_of_capex"] * r.capex
        new_bal += borrow
        internal = r.ebitda - r.tax - r.delta_nwc - interest
        gap = r.capex - borrow - internal
        cum_gap += gap
        cash = cash - gap
        debt = old + new_bal
        net = debt - max(cash, 0.0)
        out.append(CreditRow(year=r.year, debt_start=start, new_debt=borrow,
                             maturities_refinanced=maturity, interest=interest, ebitda=r.ebitda,
                             net_debt_to_ebitda=net / r.ebitda if r.ebitda > 0 else 99.0,
                             interest_coverage=r.ebitda / interest if interest > 0 else 99.0,
                             funding_gap=gap))
    return CreditResult(rows=out,
                        min_interest_coverage=min(r.interest_coverage for r in out),
                        max_net_debt_to_ebitda=max(r.net_debt_to_ebitda for r in out),
                        cumulative_funding_gap=max(0.0, cum_gap - x["cash_0"]),
                        refinancing_at_new_rate=refi_total)


def unit_economics(x: dict[str, float]) -> UnitEconomics:
    """Pre-tax, unlevered economics of one GPU bought in year 1 and run for its economic life."""
    _require(x)
    life = int(round(x["gpu_economic_life_years"]))
    facility_mw = x["kw_per_gpu"] * x["pue"] / 1000.0
    flows = [-x["capex_per_gpu"]]
    for age in range(life):
        rev = HOURS * x["utilization"] * x["price_per_gpu_hour_new"] * (1 - x["price_decay_per_year_of_age"]) ** age
        cost = (facility_mw * HOURS * x["power_cost_per_mwh"] * x["utilization"]
                + facility_mw * x["lease_cost_per_mw_year"] + x["other_opex_pct_revenue"] * rev)
        flows.append(rev - cost)
    npv = lambda r: sum(f / (1 + r) ** i for i, f in enumerate(flows))
    irr: Optional[float] = None
    lo, hi = -0.99, 5.0
    if npv(lo) * npv(hi) < 0:
        for _ in range(200):
            mid = (lo + hi) / 2
            if npv(lo) * npv(mid) <= 0:
                hi = mid
            else:
                lo = mid
        irr = (lo + hi) / 2
    cum, payback = flows[0], None
    for i, f in enumerate(flows[1:], start=1):
        if cum < 0 <= cum + f:
            payback = i - 1 + (-cum / f)
        cum += f
    return UnitEconomics(capex_per_gpu=x["capex_per_gpu"], annual_contribution_y1=flows[1],
                         cohort_irr=irr, cohort_npv_at_wacc=npv(x["wacc"]), payback_years=payback)
