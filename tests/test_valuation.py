import pytest

from icommittee.valuation.analysis import attribute, reverse_solve, sensitivity
from icommittee.valuation.model import (MissingInputError, ValuationConsistencyError, credit_projection,
                                        equity_bridge, operating_model, unit_economics, value)


def test_missing_inputs_listed_not_defaulted(inputs):
    del inputs["gross_debt_0"], inputs["wacc"]
    with pytest.raises(MissingInputError) as e:
        value(inputs)
    assert set(e.value.missing) == {"gross_debt_0", "wacc"}


@pytest.mark.parametrize("k,v", [("utilization", True), ("utilization", 85), ("wacc", float("nan")), ("bogus", 1)])
def test_bad_inputs_rejected(inputs, k, v):
    inputs[k] = v
    with pytest.raises(ValuationConsistencyError):
        value(inputs)


def test_wacc_must_exceed_growth(inputs):
    inputs.update(wacc=0.05, terminal_growth=0.045)
    with pytest.raises(ValuationConsistencyError, match="exceed"):
        value(inputs)


def test_energised_cannot_exceed_contracted(inputs):
    inputs["energized_power_mw_0"] = 3000
    with pytest.raises(ValuationConsistencyError):
        value(inputs)


def test_accounting_identities(inputs):
    v = value(inputs)
    b = v.bridge
    assert b.enterprise_value == pytest.approx(sum(r.pv_fcff for r in v.rows) + v.pv_terminal)
    assert b.equity_value == pytest.approx(b.enterprise_value + b.plus_cash - b.less_debt - b.less_leases
                                           - b.less_preferred - b.less_minority)
    assert b.value_per_share == pytest.approx(b.equity_value / b.diluted_shares)
    for r in v.rows:
        assert r.fcff == pytest.approx(r.ebit - r.tax + r.depreciation + r.writeoffs - r.capex - r.delta_nwc)


def test_deterministic(inputs):
    assert value(inputs).output_hash == value(dict(inputs)).output_hash


def test_dilution_uses_intrinsic_price(inputs):
    b = equity_bridge(60e9, inputs)
    p = b.value_per_share
    expected = inputs["basic_shares_0"] + inputs["rsus_0"] + inputs["options_0"] * (1 - inputs["options_strike"] / p)
    assert b.diluted_shares == pytest.approx(expected, rel=1e-6)
    deep_otm = dict(inputs, options_strike=10_000)
    assert equity_bridge(60e9, deep_otm).diluted_shares == pytest.approx(inputs["basic_shares_0"] + inputs["rsus_0"])


def test_negative_equity_floored(inputs):
    b = equity_bridge(1e9, inputs)
    assert b.value_per_share < 0 and b.value_per_share_floored == 0


def test_lease_double_count_refused(inputs):
    with pytest.raises(ValuationConsistencyError, match="double count"):
        equity_bridge(50e9, inputs, "debt")
    b = equity_bridge(50e9, dict(inputs, lease_cost_per_mw_year=0), "debt")
    assert b.less_leases == inputs["lease_liabilities_0"]


def test_economic_life_shorter_than_accounting_triggers_writeoffs(inputs):
    rows, _ = operating_model(dict(inputs, gpu_economic_life_years=3, gpu_useful_life_years=6))
    assert any(r.writeoffs > 0 for r in rows)
    v = value(dict(inputs, gpu_economic_life_years=3, gpu_useful_life_years=6))
    assert any("accounting life exceeds economic life" in w for w in v.warnings)


def test_monotone_in_price_and_utilisation(inputs):
    lo = value(dict(inputs, price_per_gpu_hour_new=2.8)).bridge.value_per_share
    hi = value(dict(inputs, price_per_gpu_hour_new=3.2)).bridge.value_per_share
    assert hi > lo
    assert value(dict(inputs, utilization=0.9)).bridge.value_per_share > value(inputs).bridge.value_per_share


def test_reverse_solve_round_trip(inputs):
    target = value(inputs).bridge.value_per_share
    solved = reverse_solve(dict(inputs, price_per_gpu_hour_new=2.0), "price_per_gpu_hour_new", target)
    assert solved == pytest.approx(3.0, rel=1e-4)
    assert reverse_solve(inputs, "pue", 10_000) is None  # unreachable within bounds


def test_credit_refinances_disclosed_maturities(inputs):
    c = credit_projection(inputs)
    assert c.refinancing_at_new_rate == pytest.approx(9e9)
    assert c.rows[0].interest == pytest.approx(inputs["gross_debt_0"] * inputs["avg_interest_rate_0"])


def test_unit_economics_known_case(inputs):
    x = dict(inputs, power_cost_per_mwh=0, lease_cost_per_mw_year=0, other_opex_pct_revenue=0,
             price_decay_per_year_of_age=0, gpu_economic_life_years=2, utilization=1.0, price_per_gpu_hour_new=1.0,
             capex_per_gpu=8760)
    ue = unit_economics(x)  # -8760, +8760, +8760 -> IRR = 61.8%
    assert ue.cohort_irr == pytest.approx(0.618034, rel=1e-4)
    assert ue.payback_years == pytest.approx(1.0)


def test_attribution_single_driver_explains_gap(inputs):
    a = dict(inputs)
    b = dict(inputs, utilization=0.75)
    c = dict(inputs, utilization=0.95)
    res = attribute({"a": a, "b": b, "c": c}, materiality_abs=0.01)
    assert [d.driver for d in res.disagreements] == ["utilization"]
    d = res.disagreements[0]
    assert {d.low_analyst, d.high_analyst} == {"b", "c"}
    assert all(abs(v) < 1e-6 for v in res.interaction_residuals.values())


def test_attribution_identical_views_no_disagreement(inputs):
    assert attribute({"a": inputs, "b": dict(inputs)}).disagreements == []


def test_sensitivity_grid_shape(inputs):
    g = sensitivity(inputs, "utilization", [0.7, 0.8], "price_per_gpu_hour_new", [2.5, 3.0, 3.5])
    assert len(g) == 2 and len(g[0]) == 3 and g[1][2] >= g[0][0]
