from conftest import FORECAST, SESSION, dp, make_ev

from icommittee.evidence.registry import EvidenceRegistry
from icommittee.evidence.verify import ClaimVerifier
from icommittee.schemas import Assumption, Claim, Epistemic, ScenarioSpec
from icommittee.valuation.gate import FactLayer, assemble_scenarios, gate_assumption

FACT_DPS = [dp("contracted_power_mw", 2500, "MW"), dp("active_power_mw", 900, "MW"), dp("total_debt", 20, "USD_bn"),
            dp("cash_and_equivalents", 2, "USD_bn"), dp("lease_liabilities", 15, "USD_bn"),
            dp("preferred_equity", 0, "USD"), dp("noncontrolling_interest", 0, "USD"), dp("ppe_net", 25, "USD_bn"),
            dp("basic_shares_outstanding", 500, "shares_m"), dp("unvested_rsus", 30, "shares_m"),
            dp("options_outstanding", 40, "shares_m"), dp("options_weighted_avg_strike", 10, "USD"),
            dp("weighted_avg_interest_rate", 9, "pct"), dp("debt_maturities_y1", 2, "USD_bn"),
            dp("debt_maturities_y2", 4, "USD_bn"), dp("debt_maturities_y3", 3, "USD_bn"),
            dp("adds_guide", 500, "MW", "2027", "management_guidance")]


def setup():
    reg = EvidenceRegistry(SESSION)
    reg.add(make_ev("E1", FACT_DPS))
    facts = FactLayer.from_registry(reg)
    claims = {"a.g": Claim(id="a.g", author="a", text="guide", epistemic=Epistemic.MANAGEMENT_GUIDANCE,
                           citations=["E1"], metric="adds_guide", value=500, unit="MW", period="2027"),
              "a.bad": Claim(id="a.bad", author="a", text="debt", epistemic=Epistemic.VERIFIED_FACT,
                             citations=["E1"], metric="total_debt", value=5, unit="USD_bn", period="2026-06-30")}
    checks = {c.claim_id: c for c in ClaimVerifier(reg).check_all(list(claims.values()))}
    return facts, claims, checks


def A(driver, value, epi=Epistemic.ANALYST_ASSUMPTION, basis=(), rationale="A reasoned rationale here."):
    return Assumption(driver=driver, value=value, epistemic=epi, basis_claims=list(basis), rationale=rationale)


def test_fact_layer_complete_and_normalised():
    facts, _, _ = setup()
    assert not facts.missing
    assert facts.facts["gross_debt_0"].value == 20e9 and facts.facts["avg_interest_rate_0"].value == 0.09


def test_supported_guidance_kept():
    f, c, k = setup()
    ok, find = gate_assumption(A("mw_additions_per_year", 500, Epistemic.MANAGEMENT_GUIDANCE, ["a.g"]), "base", f, c, k)
    assert ok.epistemic == Epistemic.MANAGEMENT_GUIDANCE and not find


def test_guidance_label_with_different_value_downgraded_visibly():
    f, c, k = setup()
    ok, find = gate_assumption(A("mw_additions_per_year", 600, Epistemic.MANAGEMENT_GUIDANCE, ["a.g"]), "base", f, c, k)
    assert ok.epistemic == Epistemic.ANALYST_ASSUMPTION
    assert find[0].code == "value_differs_from_source" and find[0].severity == "warning"


def test_strict_mode_rejects_mislabel():
    f, c, k = setup()
    ok, find = gate_assumption(A("mw_additions_per_year", 600, Epistemic.MANAGEMENT_GUIDANCE, ["a.g"]), "base", f, c, k,
                               strict=True)
    assert ok is None and find[0].severity == "error"


def test_basis_on_false_fact_rejected():
    f, c, k = setup()
    ok, find = gate_assumption(A("utilization", 0.9, basis=["a.bad"]), "base", f, c, k)
    assert ok is None and find[0].code == "basis_contradicted"


def test_no_rationale_rejected():
    f, c, k = setup()
    ok, find = gate_assumption(A("utilization", 0.9, rationale="ok"), "base", f, c, k)
    assert ok is None and find[0].code == "no_rationale"


def _specs(base_over=None, bear=None):
    b = {k: A(k, v) for k, v in FORECAST.items()}
    b.update(base_over or {})
    return [ScenarioSpec(name="base", probability=0.5, assumptions=b),
            ScenarioSpec(name="bear", probability=0.3, assumptions=bear or {}),
            ScenarioSpec(name="bull", probability=0.2, assumptions={})]


def test_rejected_override_makes_scenario_unvaluable_not_base():
    f, c, k = setup()
    out, find, reasons, acc, rej = assemble_scenarios(
        _specs(bear={"utilization": A("utilization", 0.5, basis=["a.bad"])}), f, c, k)
    assert out["bear"] is None and "override rejected" in reasons["bear"][0]
    assert out["base"] is not None and out["bull"] is not None
    assert "utilization" in rej["bear"]


def test_rejected_proposal_stays_rejected_on_reassembly():
    f, c, k = setup()
    specs = _specs(bear={"utilization": A("utilization", 0.5, basis=["a.bad"])})
    _, _, _, acc, rej = assemble_scenarios(specs, f, c, k)
    for s in specs:
        s.assumptions, s.rejected = acc[s.name], rej[s.name]
    out, *_ = assemble_scenarios(specs, f, c, k)
    assert out["bear"] is None


def test_bear_inherits_revised_base():
    f, c, k = setup()
    specs = _specs(base_over={"wacc": A("wacc", 0.12)})
    out, *_ = assemble_scenarios(specs, f, c, k)
    assert out["bear"]["wacc"].value == 0.12


def test_missing_driver_unvaluable():
    f, c, k = setup()
    specs = _specs()
    del specs[0].assumptions["wacc"]
    out, _, reasons, *_ = assemble_scenarios(specs, f, c, k)
    assert all(v is None for v in out.values()) and any("wacc" in r for r in reasons["base"])
