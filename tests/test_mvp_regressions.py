"""One test per weakness found in the original MVP audit, expressed against the new system."""
import pytest
from conftest import SESSION, dp, make_ev

from icommittee.agents.outputs import AnalystDraft
from icommittee.evidence.registry import EvidenceRegistry
from icommittee.evidence.verify import ClaimVerifier
from icommittee.schemas import Claim, Epistemic, Verdict
from icommittee.valuation.model import ValuationConsistencyError, equity_bridge, value


def test_w2_valid_id_wrong_number_is_caught():
    reg = EvidenceRegistry(SESSION)
    reg.add(make_ev("E1", [dp("revenue", 1000, "USD_m", "FY2025")]))
    c = Claim(id="a.1", author="a", text="Revenue was $9,999 million and grew 400%.", epistemic=Epistemic.VERIFIED_FACT,
              citations=["E1"], metric="revenue", value=9999, unit="USD_m", period="FY2025")
    assert ClaimVerifier(reg).check(c).verdict == Verdict.VALUE_MISMATCH


def test_w2_citations_are_structured_not_regex_parsed():
    # "[E1, E42]" can't slip through: citations are a typed list and each id is looked up.
    reg = EvidenceRegistry(SESSION)
    reg.add(make_ev("E1"))
    c = Claim(id="a.1", author="a", text="x", epistemic=Epistemic.VERIFIED_FACT, citations=["E1", "E42"])
    assert ClaimVerifier(reg).check(c).verdict == Verdict.UNKNOWN_CITATION


def test_w4_negative_equity_not_reported_as_negative_price(inputs):
    b = equity_bridge(1e9, inputs)
    assert b.value_per_share_floored == 0.0


def test_w4_booleans_and_absurd_values_rejected(inputs):
    for bad in (dict(inputs, capex_per_gpu=True), dict(inputs, utilization=5.0)):
        with pytest.raises(ValuationConsistencyError):
            value(bad)


def test_w4_valuation_is_discounted(inputs):
    v = value(inputs)
    assert v.rows[0].discount_factor == pytest.approx(1 / (1 + inputs["wacc"]))
    assert v.bridge.diluted_shares > inputs["basic_shares_0"]  # dilution actually computed


def test_w5_llm_output_must_validate():
    with pytest.raises(ValueError):
        AnalystDraft.model_validate({"thesis": "t", "stance": "positive", "key_points": [], "claims": [],
                                     "scenarios": [{"name": "base", "probability": 1.0, "assumptions": []}],
                                     "uncertainties": [], "invalidation_triggers": []})
