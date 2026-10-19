import json

import pytest

from icommittee.cli import main
from icommittee.eval.harness import cases, run_demo, valuation_consistency
from icommittee.schemas import Recommendation


@pytest.fixture(scope="module")
def demo():
    return run_demo()


def test_all_five_analysts_report(demo):
    assert sorted(demo.reports_v1) == ["contrarian", "credit", "growth", "industry", "value"]


def test_analysts_blind_to_price_in_stage1(demo):
    assert all("EV-004" not in r.evidence_seen for r in demo.reports_v1.values())


def test_diverse_views_differ_but_share_primary_facts(demo):
    seen = {k: set(r.evidence_seen) for k, r in demo.reports_v1.items()}
    assert seen["growth"] != seen["industry"]
    assert {"EV-001", "EV-013"} <= set.intersection(*seen.values())


def test_hallucination_blocks_dependent_scenario_then_fix_clears_it(demo):
    assert demo.reports_v1["growth"].valuations["bull"] is None
    assert demo.reports_v2["growth"].valuations["bull"] is not None


def test_revision_flows_into_bear_and_bull(demo):
    # Growth revised base price decay; bear/bull must inherit it.
    v2 = demo.reports_v2["growth"]
    assert v2.scenario("base").assumptions["price_decay_per_year_of_age"].value == 0.15
    assert "price_decay_per_year_of_age" not in v2.scenario("bear").assumptions


def test_decision_numbers_come_from_code(demo):
    d = demo.decision
    assert d.valuation_low <= d.valuation_base <= d.valuation_high
    assert d.recommendation == d.rule_based_recommendation  # no override in the fixture


def test_dissent_preserved(demo):
    assert {x.role for x in demo.decision.dissents} and all(x.thesis for x in demo.decision.dissents)


def test_reproducible(demo):
    assert run_demo().decision_fingerprint() == demo.decision_fingerprint()


def test_stored_valuations_recompute(demo):
    v = valuation_consistency(demo)
    assert v["checked"] > 20 and not v["failures"]


def test_synthetic_is_flagged(demo):
    assert demo.synthetic and any("synthetic" in f for f in demo.decision.lint_flags)


def test_cli_demo_writes_outputs(tmp_path):
    assert main(["demo", "--out", str(tmp_path)]) == 0
    assert (tmp_path / "report.md").read_text().startswith("# Investment Committee")
    data = json.loads((tmp_path / "results.json").read_text())
    assert data["decision"]["recommendation"] in {r.value for r in Recommendation}
    assert (tmp_path / "audit.jsonl").stat().st_size > 0


@pytest.mark.parametrize("case", cases(), ids=lambda c: c.name)
def test_adversarial(case):
    ok, detail = case.run()
    assert ok, detail
