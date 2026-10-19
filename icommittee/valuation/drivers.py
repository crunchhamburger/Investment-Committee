"""Driver catalogue for the GPU-cloud operating model.

Every model input is declared here with units and plausibility bounds.
`fact` drivers come only from the evidence registry (balance sheet, share
count, installed capacity); analysts cannot override them. `forecast`
drivers are analyst-owned assumptions.

Bounds are *plausibility* guards against typos, unit errors and
hallucinations, not views. They are deliberately wide.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional


@dataclass(frozen=True)
class DriverSpec:
    name: str
    unit: str
    lo: float
    hi: float
    kind: Literal["fact", "forecast"]
    description: str
    fact_metric: Optional[str] = None


_F = "fact"
_A = "forecast"

DRIVERS: dict[str, DriverSpec] = {d.name: d for d in [
    # ---- facts: starting position at the valuation date ----
    DriverSpec("contracted_power_mw_0", "MW", 0, 50_000, _F, "Contracted data-centre power", "contracted_power_mw"),
    DriverSpec("energized_power_mw_0", "MW", 0, 50_000, _F, "Active (energised) power", "active_power_mw"),
    DriverSpec("gross_debt_0", "USD", 0, 1e12, _F, "Total debt incl. current portion", "total_debt"),
    DriverSpec("cash_0", "USD", 0, 1e12, _F, "Cash and equivalents", "cash_and_equivalents"),
    DriverSpec("lease_liabilities_0", "USD", 0, 1e12, _F, "Operating + finance lease liabilities", "lease_liabilities"),
    DriverSpec("preferred_0", "USD", 0, 1e12, _F, "Preferred equity", "preferred_equity"),
    DriverSpec("minority_interest_0", "USD", 0, 1e12, _F, "Non-controlling interest", "noncontrolling_interest"),
    DriverSpec("existing_ppe_net_0", "USD", 0, 1e12, _F, "Net PP&E", "ppe_net"),
    DriverSpec("basic_shares_0", "shares", 1, 1e11, _F, "Basic shares outstanding", "basic_shares_outstanding"),
    DriverSpec("rsus_0", "shares", 0, 1e10, _F, "Unvested RSUs", "unvested_rsus"),
    DriverSpec("options_0", "shares", 0, 1e10, _F, "Options outstanding", "options_outstanding"),
    DriverSpec("options_strike", "USD", 0, 1e5, _F, "Weighted average option strike", "options_weighted_avg_strike"),
    DriverSpec("avg_interest_rate_0", "fraction", 0, 0.30, _F, "Weighted average rate on existing debt", "weighted_avg_interest_rate"),
    DriverSpec("debt_maturity_y1", "USD", 0, 1e12, _F, "Debt maturing in forecast year 1", "debt_maturities_y1"),
    DriverSpec("debt_maturity_y2", "USD", 0, 1e12, _F, "Debt maturing in forecast year 2", "debt_maturities_y2"),
    DriverSpec("debt_maturity_y3", "USD", 0, 1e12, _F, "Debt maturing in forecast year 3", "debt_maturities_y3"),
    # ---- forecasts: capacity ----
    DriverSpec("mw_additions_per_year", "MW", 0, 10_000, _A, "New contracted MW signed per year"),
    DriverSpec("energization_rate", "fraction", 0.05, 1.0, _A,
               "Share of contracted-but-not-live MW brought online each year (power-to-compute conversion)"),
    DriverSpec("pue", "x", 1.0, 2.0, _A, "Power usage effectiveness (facility MW / IT MW)"),
    DriverSpec("kw_per_gpu", "kW", 0.3, 5.0, _A, "All-in IT kW per GPU incl. networking and CPU"),
    DriverSpec("existing_fleet_avg_age", "years", 0, 6, _A, "Average age of installed GPUs at t0"),
    # ---- forecasts: pricing & utilisation ----
    DriverSpec("utilization", "fraction", 0.05, 1.0, _A, "Share of GPU-hours sold"),
    DriverSpec("price_per_gpu_hour_new", "USD_per_hour", 0.10, 25.0, _A, "Blended price per GPU-hour for newest generation, year 1"),
    DriverSpec("price_new_growth_per_year", "fraction", -0.30, 0.30, _A, "Annual change in newest-generation GPU-hour price"),
    DriverSpec("price_decay_per_year_of_age", "fraction", 0.0, 0.60, _A, "Price discount per year of GPU age (generation obsolescence)"),
    # ---- forecasts: costs & capital ----
    DriverSpec("power_cost_per_mwh", "USD_per_MWh", 0, 400, _A, "Electricity cost"),
    DriverSpec("lease_cost_per_mw_year", "USD", 0, 1e7, _A, "Facility lease cost per energised MW per year"),
    DriverSpec("other_opex_pct_revenue", "fraction", 0, 0.9, _A, "Other cash opex as share of revenue"),
    DriverSpec("capex_per_gpu", "USD", 2_000, 200_000, _A, "All-in capex per GPU incl. networking"),
    DriverSpec("gpu_useful_life_years", "years", 2, 10, _A, "Accounting depreciation life"),
    DriverSpec("gpu_economic_life_years", "years", 2, 10, _A, "Economic life before retirement/replacement"),
    DriverSpec("existing_ppe_remaining_life", "years", 1, 10, _A, "Remaining depreciation life of existing PP&E"),
    DriverSpec("tax_rate", "fraction", 0, 0.45, _A, "Cash tax rate on positive EBIT"),
    DriverSpec("nwc_pct_revenue_change", "fraction", -0.5, 0.5, _A, "Net working capital investment per $ of revenue growth"),
    # ---- forecasts: discounting & financing ----
    DriverSpec("wacc", "fraction", 0.04, 0.25, _A, "Weighted average cost of capital"),
    DriverSpec("terminal_growth", "fraction", -0.05, 0.05, _A, "Perpetual growth after the forecast horizon"),
    DriverSpec("debt_funded_share_of_capex", "fraction", 0, 1, _A, "Share of capex funded with new debt (credit view)"),
    DriverSpec("new_debt_rate", "fraction", 0, 0.25, _A, "Rate on new and refinanced debt"),
]}

FACT_DRIVERS = [k for k, d in DRIVERS.items() if d.kind == "fact"]
FORECAST_DRIVERS = [k for k, d in DRIVERS.items() if d.kind == "forecast"]
UNIT_FAMILY_OF_DRIVER = {
    "MW": "MW", "USD": "USD", "shares": "shares", "fraction": "fraction", "x": "x",
    "kW": "kW", "years": "years", "USD_per_hour": "USD_per_hour", "USD_per_MWh": "USD_per_MWh",
}


def catalogue_text(kinds=("forecast",)) -> str:
    lines = []
    for d in DRIVERS.values():
        if d.kind in kinds:
            lines.append(f"- {d.name} [{d.unit}, {d.lo:g}..{d.hi:g}]: {d.description}")
    return "\n".join(lines)
