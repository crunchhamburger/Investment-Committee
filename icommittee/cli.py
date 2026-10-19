"""Command-line entry point.

  python -m icommittee demo                      # offline, scripted fixtures
  python -m icommittee check  --dossier FILE     # data QA only: statuses, conflicts, facts layer
  python -m icommittee run    --dossier FILE     # live LLMs (set ICOMMITTEE_MODEL[_ROLE])
  python -m icommittee sec    --ticker T --out FILE   # draft dossier from SEC XBRL (needs network)
  python -m icommittee eval   [--repeats N]      # adversarial suite + reproducibility
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import RiskPolicy, Settings
from .evidence.registry import EvidenceRegistry
from .ingest.fixtures import load_dossier
from .llm.client import StructuredLLM
from .llm.transports import make_transport_factory
from .pipeline.committee import Committee
from .reporting.markdown import render
from .valuation.gate import FactLayer

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "fixtures" / "demo"


def build(dossier: Path, fixture_dir: Path | None, policy: Path | None, settings_override=None,
          mutate=None, cache: bool = True):
    company, sd, evs = load_dossier(dossier)
    # Fixture runs ignore model env vars so the demo is always offline and deterministic.
    s = settings_override or (Settings(session_date=sd) if fixture_dir is not None else Settings.from_env(sd))
    s.session_date = sd
    reg = EvidenceRegistry(sd)
    reg.extend(evs)
    llm = StructuredLLM(model_for=s.model_for, transport_for=make_transport_factory(fixture_dir, mutate),
                        cache_dir=(s.cache_dir if cache and fixture_dir is None else None),
                        timeout_s=s.timeout_s, max_retries=s.max_retries, temperature=s.temperature,
                        pricing=s.cost_per_mtok)
    return Committee(reg, llm, s, RiskPolicy.load(policy), company=company), reg


def write_outputs(res, reg, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.md").write_text(render(res, reg))
    (out / "results.json").write_text(json.dumps(res.to_json(), indent=1, default=str))
    with (out / "audit.jsonl").open("w") as f:
        for e in res.events:
            f.write(json.dumps(e, default=str) + "\n")
    with (out / "evidence_snapshot.jsonl").open("w") as f:
        for e in reg.all():
            f.write(e.model_dump_json() + "\n")


def summarise(res) -> str:
    d = res.decision
    vals = ", ".join(f"{r}: {v.value('base'):.2f}" if v.value("base") is not None else f"{r}: n/a"
                     for r, v in res.reports_v2.items())
    return (f"Decision: {d.recommendation.value.upper()} (rule-based {d.rule_based_recommendation.value}); "
            f"range p10/mean/p90 = {d.valuation_low}, {d.valuation_base}, {d.valuation_high}; price {d.market_price}\n"
            f"Base values: {vals}\nFlags: {d.lint_flags}")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="icommittee", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("demo")
    d.add_argument("--out", type=Path, default=Path("committee_output/demo"))
    d.add_argument("--policy", type=Path, default=ROOT / "config" / "risk_policy.yaml")
    c = sub.add_parser("check")
    c.add_argument("--dossier", type=Path, required=True)
    r = sub.add_parser("run")
    r.add_argument("--dossier", type=Path, required=True)
    r.add_argument("--out", type=Path, default=Path("committee_output/run"))
    r.add_argument("--policy", type=Path, default=ROOT / "config" / "risk_policy.yaml")
    sc = sub.add_parser("sec")
    sc.add_argument("--ticker", required=True)
    sc.add_argument("--out", type=Path, required=True)
    sc.add_argument("--session-date")
    e = sub.add_parser("eval")
    e.add_argument("--repeats", type=int, default=2)
    e.add_argument("--out", type=Path, default=Path("committee_output/eval"))
    a = p.parse_args(argv)

    if a.cmd == "demo":
        com, reg = build(DEMO / "evidence.json", DEMO / "llm", a.policy)
        res = com.run()
        write_outputs(res, reg, a.out)
        print(summarise(res))
        print(f"Report: {a.out / 'report.md'}")
    elif a.cmd == "check":
        company, sd, evs = load_dossier(a.dossier)
        reg = EvidenceRegistry(sd)
        reg.extend(evs)
        print(f"{company} | session {sd} | snapshot {reg.snapshot_hash()}")
        for ev in reg.all():
            print(f"  {ev.id:8s} {reg.status(ev.id):10s} {ev.tier.value:9s} {ev.as_of} {','.join(ev.flags)} {ev.title}")
        for cf in reg.conflicts():
            print(f"  CONFLICT {cf.metric} {cf.period}: {cf.values} -> {cf.resolved_by or 'UNRESOLVED'} ({cf.reason})")
        fl = FactLayer.from_registry(reg)
        for k, v in fl.facts.items():
            print(f"  fact {k} = {v.value:,.6g} ({v.evidence_ids[0]})")
        for k, why in fl.missing.items():
            print(f"  MISSING {k}: {why}")
        return 1 if fl.missing else 0
    elif a.cmd == "run":
        com, reg = build(a.dossier, None, a.policy)
        if all(com.s.model_for(x) == "fixture" for x in ("value", "chair")):
            print("Set ICOMMITTEE_MODEL (e.g. anthropic:<model> or openai:<model>) for live runs.", file=sys.stderr)
            return 2
        res = com.run()
        write_outputs(res, reg, a.out)
        print(summarise(res))
    elif a.cmd == "sec":
        from .ingest.sec import build_dossier
        build_dossier(a.ticker, a.out, a.session_date)
        print(f"Draft dossier written to {a.out}. Run `check` on it; operational facts (MW, maturities, "
              "dilution) and a market price must be added from primary sources by hand.")
    elif a.cmd == "eval":
        from .eval.harness import run_all
        report = run_all(a.repeats)
        a.out.mkdir(parents=True, exist_ok=True)
        (a.out / "eval.json").write_text(json.dumps(report, indent=1, default=str))
        (a.out / "eval.md").write_text(report["markdown"])
        print(report["markdown"])
        return 0 if report["adversarial"]["caught"] == report["adversarial"]["total"] else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
