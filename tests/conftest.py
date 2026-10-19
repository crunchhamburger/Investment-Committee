import sys
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from icommittee.schemas import DataPoint, Epistemic, Evidence, SourceKind, SourceTier  # noqa: E402

SESSION = date(2026, 10, 9)


def make_ev(id, datapoints=(), tier="primary", kind="sec_filing", published="2026-08-10", as_of="2026-06-30",
            excerpt="Filing text.", **kw):
    return Evidence(id=id, title=f"doc {id}", publisher="pub", url=f"fixture://{id}", tier=SourceTier(tier),
                    kind=SourceKind(kind), published=date.fromisoformat(published),
                    retrieved_at=datetime(2026, 10, 9, tzinfo=timezone.utc), as_of=date.fromisoformat(as_of),
                    excerpt=excerpt, datapoints=[DataPoint(**d) for d in datapoints], **kw)


def dp(metric, value, unit, period="2026-06-30", basis="verified_fact"):
    return dict(metric=metric, value=value, unit=unit, period=period, basis=Epistemic(basis))


FACTS = dict(contracted_power_mw_0=2500, energized_power_mw_0=900, gross_debt_0=20e9, cash_0=2e9,
             lease_liabilities_0=15e9, preferred_0=0, minority_interest_0=0, existing_ppe_net_0=25e9,
             basic_shares_0=500e6, rsus_0=30e6, options_0=40e6, options_strike=10.0, avg_interest_rate_0=0.09,
             debt_maturity_y1=2e9, debt_maturity_y2=4e9, debt_maturity_y3=3e9)
FORECAST = dict(mw_additions_per_year=450, energization_rate=0.35, pue=1.3, kw_per_gpu=1.4, existing_fleet_avg_age=1,
                utilization=0.85, price_per_gpu_hour_new=3.0, price_new_growth_per_year=0.0,
                price_decay_per_year_of_age=0.12, power_cost_per_mwh=65, lease_cost_per_mw_year=1.2e6,
                other_opex_pct_revenue=0.12, capex_per_gpu=40000, gpu_useful_life_years=6, gpu_economic_life_years=6,
                existing_ppe_remaining_life=5, tax_rate=0.21, nwc_pct_revenue_change=0.05, wacc=0.105,
                terminal_growth=0.025, debt_funded_share_of_capex=0.7, new_debt_rate=0.085)


@pytest.fixture
def inputs():
    return {**FACTS, **FORECAST}
