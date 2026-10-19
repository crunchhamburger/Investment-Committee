"""Markdown report. Order: decision first, then everything needed to audit it."""
from __future__ import annotations

from collections import Counter

from ..evidence.registry import EvidenceRegistry
from ..pipeline.committee import SessionResult


def _m(x, fmt="{:,.2f}"):
    if x is None or x != x:
        return "n/a"
    return fmt.format(x)


def _pct(x):
    return _m(x, "{:.1%}")


def _bn(x):
    return _m(None if x is None else x / 1e9, "${:,.1f}bn")


def render(res: SessionResult, reg: EvidenceRegistry) -> str:
    d, rk = res.decision, res.risk
    L = []
    w = L.append
    w(f"# Investment Committee: {res.company}")
    if res.synthetic:
        w("> **SYNTHETIC DATA. Not investable.** All evidence and LLM outputs in this run are scripted fixtures. "
          "They exercise the pipeline's controls; they are not evidence that the committee works.")
    w(f"Session date **{res.session_date}** · registry snapshot `{res.registry_hash}` · price: "
      f"{_m(d.market_price, '${:,.2f}')} ({res.diagnostics.get('price_note') or 'n/a'}). "
      "Prices are end-of-day as recorded in the registry, not real-time.")

    w("\n## Decision")
    w(f"**{d.recommendation.value.upper()}**"
      + (f" (rule-based: {d.rule_based_recommendation.value}; chair override)" if d.chair_override else ""))
    w("")
    w("| Valuation p10 | Probability-weighted | p90 | Price | Expected return | Position size |")
    w("|---|---|---|---|---|---|")
    w(f"| {_m(d.valuation_low, '${:,.2f}')} | {_m(d.valuation_base, '${:,.2f}')} | {_m(d.valuation_high, '${:,.2f}')} "
      f"| {_m(d.market_price, '${:,.2f}')} | {_pct(d.expected_return)} | "
      f"{_pct(d.position_size_fraction) if d.position_size_fraction is not None else 'none'} |")
    w("\nWhy: " + "; ".join(d.reasons))
    w(f"\nSizing basis: {d.position_size_basis}.")
    if d.lint_flags:
        w("\n**Process flags:** " + "; ".join(f"`{f}`" for f in d.lint_flags))
    w("\n**Primary thesis.** " + d.primary_thesis)
    w("\n**Strongest opposing thesis.** " + d.strongest_opposing_thesis)
    for title, items in (("Catalysts", d.catalysts), ("Key risks", d.key_risks),
                         ("Unresolved questions", d.unresolved_questions)):
        if items:
            w(f"\n**{title}**\n" + "\n".join(f"- {i}" for i in items))
    w("\n**Reconsideration triggers**\n" + "\n".join(
        f"- {t.description} (`{t.metric} {t.operator} {t.threshold:g} {t.unit}`)" for t in d.reconsideration_triggers))
    if d.dissents:
        w("\n### Dissent (preserved, not averaged away)")
        w("| Analyst | Expected value/share | Implied view | Thesis |\n|---|---|---|---|")
        for x in d.dissents:
            w(f"| {x.role} | {_m(x.expected_value_per_share, '${:,.2f}')} | {x.implied_view.value} | {x.thesis} |")

    w("\n## Risk review")
    w(f"Veto: **{'YES' if rk.veto else 'no'}** · P(impairment): {_pct(rk.probability_of_impairment)} · "
      f"analyst dispersion: {_pct(rk.model_dispersion)}")
    w("\n| Rule | Metric | Observed | Threshold | Pass | Action |\n|---|---|---|---|---|---|")
    for r in rk.rule_results:
        w(f"| {r.rule} | {r.metric} | {_m(r.observed, '{:,.3f}')} | {r.threshold:g} | {'✓' if r.passed else '✗'} | {r.action} |")
    w(f"\n{rk.narrative}")
    if rk.additional_risks:
        w("\nRisks outside the model:\n" + "\n".join(f"- {x}" for x in rk.additional_risks))

    w("\n## Disagreements that move value")
    if res.attribution:
        a = res.attribution
        w(f"Reference (median-assumption) value: {_m(a.reference_value_per_share, '${:,.2f}')}/share (unfloored).")
        w("\n| Driver | Spread $/share | Low | High | Kind | Note |\n|---|---|---|---|---|---|")
        for x in a.disagreements:
            lo = next(e for e in x.effects if e.analyst == x.low_analyst)
            hi = next(e for e in x.effects if e.analyst == x.high_analyst)
            w(f"| {x.driver} | {x.spread_per_share:,.2f} | {x.low_analyst} ({lo.value:g}) | "
              f"{x.high_analyst} ({hi.value:g}) | {x.kind} | {x.note} |")
        w("\nInteraction residuals (gap not explained by one-at-a-time swaps): "
          + ", ".join(f"{k} {v:+.2f}" for k, v in a.interaction_residuals.items()))
    else:
        w("Not computed (fewer than two valued base cases).")

    w("\n## Cross-examination")
    for c in res.challenges:
        w(f"- **{c.id}**: {c.question}"
          + (f" *(counter {c.counter_value:g})*" if c.counter_value is not None else "")
          + (f" [{', '.join(c.evidence_ids)}]" if c.evidence_ids else " [no evidence cited]")
          + f"\n  - Response ({'concedes' if c.concedes else 'holds'}): {c.response or '(none)'}")

    w("\n## Belief revision")
    w("| Analyst | Scenario | Driver | Old → New | Accepted | Flags | Basis |\n|---|---|---|---|---|---|---|")
    for role, rv in res.revisions.items():
        for ch in rv.changes:
            w(f"| {role} | {ch.scenario} | {ch.driver} | {_m(ch.old_value, '{:g}')} → {ch.new_value:g} | "
              f"{'yes' if ch.accepted else '**no**'} | {'; '.join(ch.flags) or '-'} | "
              f"{', '.join(ch.basis_challenge_ids + ch.basis_evidence_ids) or '-'} |")
        if not rv.changes:
            w(f"| {role} | - | - | retained | - | - | {rv.retained_view_reason or ''} |")
    w("\n| Analyst | Base before | Base after | Expected before | Expected after |\n|---|---|---|---|---|")
    for role, rv in res.revisions.items():
        w(f"| {role} | {_m(rv.value_before)} | {_m(rv.value_after)} | {_m(rv.expected_before)} | {_m(rv.expected_after)} |")

    w("\n## Analyst reports (final versions)")
    for role, r in res.reports_v2.items():
        w(f"\n### {role} (v{r.version}, model `{r.model}`): {r.stance}")
        w(r.thesis)
        w(f"\nValue/share: bear {_m(r.value('bear'))} · base {_m(r.value('base'))} · bull {_m(r.value('bull'))} · "
          f"expected {_m(r.expected_value())}")
        for n, why in r.unvaluable_reasons.items():
            w(f"- **{n} not valued:** " + "; ".join(why))
        w("\n| Claim | Label | Verdict | Detail |\n|---|---|---|---|")
        for cl, ck in zip(r.claims, r.claim_checks):
            w(f"| {cl.text} | {cl.epistemic.value} | **{ck.verdict.value}** | {ck.detail} |")
        if r.gate_findings:
            w("\nAssumption gate:\n" + "\n".join(
                f"- {f.severity.upper()} `{f.code}` {f.scenario}/{f.driver}: {f.detail}" for f in r.gate_findings))
        base = r.scenario("base")
        v = r.valuations.get("base")
        if base and v:
            w("\n<details><summary>Base-case drivers and model rows</summary>\n")
            w("| Driver | Value | Label | Rationale |\n|---|---|---|---|")
            for k, a in sorted(base.assumptions.items()):
                w(f"| {k} | {a.value:g} | {a.epistemic.value} | {a.rationale} |")
            w("\n| Yr | Energised MW | GPUs (k) | Revenue | EBITDA | Capex | FCFF |\n|---|---|---|---|---|---|---|")
            for row in v.rows:
                w(f"| {row.year} | {row.energized_mw:,.0f} | {row.gpus / 1e3:,.0f} | {_bn(row.revenue)} | "
                  f"{_bn(row.ebitda)} | {_bn(row.capex)} | {_bn(row.fcff)} |")
            b = v.bridge
            w(f"\nEV {_bn(b.enterprise_value)} + cash {_bn(b.plus_cash)} − debt {_bn(b.less_debt)} − leases "
              f"{_bn(b.less_leases)} (treatment: {b.lease_treatment}) − preferred {_bn(b.less_preferred)} − minority "
              f"{_bn(b.less_minority)} = equity {_bn(b.equity_value)}; diluted shares {b.diluted_shares / 1e6:,.1f}m "
              f"→ {_m(b.value_per_share, '${:,.2f}')}. Terminal value is {_pct(v.terminal_share_of_ev)} of EV. "
              f"Inputs hash `{v.input_hash}`.")
            if v.warnings:
                w("\n" + "\n".join(f"- ⚠ {x}" for x in v.warnings))
            w("\n</details>")

    w("\n## Diagnostics")
    rev = res.diagnostics.get("reverse_dcf") or {}
    if rev:
        w("**What the price implies** (one driver at a time, others at committee median):\n")
        w("| Driver | Median assumption | Value that justifies price |\n|---|---|---|")
        for k, v in rev.items():
            w(f"| {k} | {v['median_assumption']:g} | {_m(v['value_that_justifies_price'], '{:.4g}')} |")
    ue = res.diagnostics.get("unit_economics")
    if ue:
        w(f"\n**GPU cohort economics** (median case, pre-tax, unlevered): capex {_m(ue['capex_per_gpu'], '${:,.0f}')}, "
          f"year-1 contribution {_m(ue['annual_contribution_y1'], '${:,.0f}')}, IRR {_pct(ue['cohort_irr'])}, "
          f"NPV at WACC {_m(ue['cohort_npv_at_wacc'], '${:,.0f}')}, payback {_m(ue['payback_years'], '{:.1f}')} years.")
    cr = res.diagnostics.get("credit")
    if cr:
        w(f"\n**Credit (median case):** min coverage {cr['min_interest_coverage']:.2f}x, peak net debt/EBITDA "
          f"{cr['max_net_debt_to_ebitda']:.2f}x, external funding needed beyond cash {_bn(cr['cumulative_funding_gap'])}, "
          f"refinanced at new rates {_bn(cr['refinancing_at_new_rate'])}.")
    sens = res.diagnostics.get("sensitivity_price_x_utilization")
    if sens:
        w("\n**Value per share: utilization (rows) × newest-gen $/GPU-hour (columns)**\n")
        w("| util \\ price | " + " | ".join(f"{p:g}" for p in sens["cols_price"]) + " |")
        w("|---" * (len(sens["cols_price"]) + 1) + "|")
        for u, row in zip(sens["rows_utilization"], sens["grid"]):
            w(f"| {u:g} | " + " | ".join(_m(c) for c in row) + " |")

    w("\n## Evidence registry")
    w("| ID | Title | Tier | Kind | Published | As of | Status | Flags |\n|---|---|---|---|---|---|---|---|")
    for e in reg.all():
        w(f"| {e.id} | {e.title} | {e.tier.value} | {e.kind.value} | {e.published} | {e.as_of} | "
          f"{reg.status(e.id)} | {', '.join(e.flags) or '-'} |")
    w("\nStarting-position facts used by every analyst: " + ", ".join(f"`{k}`={v:,.4g}" for k, v in res.facts.items()))
    if res.facts_missing:
        w("\n**Missing facts:** " + "; ".join(f"{k} ({v})" for k, v in res.facts_missing.items()))

    w("\n## Process integrity")
    all_checks = [c for r in res.reports_v2.values() for c in r.claim_checks]
    cnt = Counter(c.verdict.value for c in all_checks)
    w("Claim verdicts (final reports): " + ", ".join(f"{k} {v}" for k, v in sorted(cnt.items())))
    rejected = sum(1 for r in res.reports_v1.values() for f in r.gate_findings if f.severity == "error")
    w(f"\nAssumptions rejected at the gate (initial reports): {rejected}")
    if res.diagnostics.get("shared_model_warning"):
        w("\n⚠ **All five analysts use the same model** "
          f"(`{res.diagnostics['models_by_role']['value']}`). Their errors are correlated; treat agreement as one "
          "opinion, not five. Configure different providers per role to reduce this.")
    llm = res.llm
    w(f"\nLLM calls: {llm['calls']} (cache hits {llm['cache_hits']}, retries {llm['retries']}, schema repairs "
      f"{llm['repairs']}), tokens in/out {llm['input_tokens']:,}/{llm['output_tokens']:,}, cost "
      f"{_m(llm['cost_usd'], '${:,.4f}') if llm['cost_usd'] is not None else 'n/a (no pricing configured)'}, "
      f"latency {llm['latency_s']}s.")
    w("\n## Limitations\nSee `docs/LIMITATIONS.md`. Key ones: one-at-a-time attribution ignores interactions "
      "(residuals shown above); equal analyst weighting is not a calibrated probability; qualitative claims are not "
      "verified without a support judge; the model is annual with a constant WACC.")
    return "\n".join(L) + "\n"
