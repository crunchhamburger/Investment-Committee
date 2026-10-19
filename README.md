# AI Investment Committee (v0.2)

A research workflow in which five differently motivated LLM analysts propose and defend **assumptions**, while
deterministic code verifies their claims, gates their inputs, computes valuations, finds the disagreements that
move value, audits belief revisions and applies written risk rules. The aim is better-tested theses, not
consensus.

> Status: every deterministic component and control is tested offline (104 tests, 24/24 adversarial cases).
> Live LLM and live SEC paths are implemented but **untested**. The demo uses scripted fixtures and synthetic
> data; it shows the controls working, not that LLM debate works. That's the experiment in `docs/EVALUATION.md`.

## Quick start

```bash
pip install -r requirements.txt          # pydantic, PyYAML, pytest; add openai and/or anthropic for live runs
python -m icommittee demo                # offline end-to-end → committee_output/demo/report.md
python -m pytest -q                      # 104 tests
python -m icommittee eval                # adversarial suite + reproducibility + debate metrics
```

## Real runs

```bash
export SEC_USER_AGENT="Your Name you@example.com"
python -m icommittee sec --ticker CRWV --out dossiers/crwv.json --session-date 2026-10-09
#   → add MW, maturities, dilution detail, RPO buckets and a dated price from primary sources (see docs/COREWEAVE_PLAN.md)
python -m icommittee check --dossier dossiers/crwv.json     # must show no MISSING facts before spending on LLMs

export ANTHROPIC_API_KEY=... OPENAI_API_KEY=...
export ICOMMITTEE_MODEL="anthropic:<model-id>"              # default for all seats
export ICOMMITTEE_MODEL_GROWTH="openai:<model-id>"          # mix providers to reduce correlated reasoning
export ICOMMITTEE_MODEL_CONTRARIAN="openai:<model-id>"
export ICOMMITTEE_STRICT_GATE=1                             # recommended for first real runs
python -m icommittee run --dossier dossiers/crwv.json --out committee_output/crwv
```

Other settings (`icommittee/config.py`): `ICOMMITTEE_TIMEOUT_S`, `ICOMMITTEE_MAX_RETRIES`, `ICOMMITTEE_TEMPERATURE`,
`ICOMMITTEE_BLIND_STAGE1`, `ICOMMITTEE_DIVERSE_VIEWS`, `ICOMMITTEE_CACHE_DIR`,
`ICOMMITTEE_PRICING="model=in:out,..."` (USD per million tokens). Risk policy: `config/risk_policy.yaml`.
No credentials are read from files.

## How a run works

1. **Registry.** Evidence is loaded point-in-time: documents published after the session date are invisible,
   superseded ones are excluded, conflicts are detected, injection-like text is flagged.
2. **Fact layer.** Balance sheet, shares and installed MW come only from primary verified datapoints. Missing
   means missing: the model refuses to run rather than default.
3. **Stage 1.** Five analysts, price withheld, each with a role-specific secondary-evidence view, return
   structured claims, driver proposals for bear/base/bull, and measurable invalidation triggers.
4. **Verification and gate.** Every quantitative claim is matched against a datapoint. Assumptions are bounded,
   honestly labelled and blocked if they rest on a failed claim.
5. **Valuation.** A GPU-cloud operating model (contracted MW → energised MW → GPUs → GPU-hours × utilisation ×
   age-decayed price), DCF, EV→equity bridge with intrinsic-price dilution, credit projection, cohort IRR.
6. **Stage 2.** Code attributes value gaps to individual drivers and labels each disagreement as interpretation,
   information asymmetry or assumption.
7. **Stage 3.** Targeted cross-examination on the top disagreements only.
8. **Stage 4.** Revisions must cite a challenge or evidence; moves toward the median without new evidence are
   flagged.
9. **Stage 5.** Risk rules from policy; only listed rules can veto.
10. **Stage 6.** Range, expected return and recommendation are computed. The chair writes the narrative; overrides
    are constrained; consensus-as-evidence is flagged; dissent is preserved.

## Docs
- `docs/AUDIT.md`: what was wrong with the MVP
- `docs/ARCHITECTURE.md`: design, module map, which seats need an LLM, failure-mode defences
- `docs/EVALUATION.md`: metrics and the experiment that tests the core proposition
- `docs/LIMITATIONS.md`: read before trusting output
- `docs/ROADMAP.md`: next, later, remove
- `docs/COREWEAVE_PLAN.md`: mapping your CRWV questions to the model

## Layout
```
icommittee/  schemas, config, cli
  evidence/  registry, verify, sanitize
  valuation/ drivers, model, gate, analysis
  llm/       client (cache/retry/repair/cost), transports (fixture/openai/anthropic)
  agents/    roles, outputs (LLM schemas), prompts
  pipeline/  committee (six stages)
  risk/      rules
  reporting/ markdown
  ingest/    sec, fixtures
  eval/      harness
fixtures/demo/  synthetic dossier + scripted LLM responses (make_fixtures.py regenerates)
config/risk_policy.yaml
tests/
example_output/  demo report and eval report from this build
```
