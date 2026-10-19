# Limitations (read before trusting any output)

## What has and hasn't been tested
- **Tested offline:** every deterministic component and every control, using scripted LLM fixtures. 104 unit and
  integration tests; 24/24 adversarial cases caught.
- **Not tested:** live OpenAI or Anthropic calls (no keys, no network in the build environment); live SEC download
  (blocked by the build environment's allowlist; the extractor is tested on mocked XBRL payloads). Expect first live
  runs to surface schema-compliance problems, mitigated by one automatic repair attempt.
- **The demo proves mechanics, not judgement.** Fixture analysts were written to contain specific errors. That the
  system catches them says nothing about whether real LLM analysts find real weaknesses.

## Verification
- Qualitative claims ("demand is accelerating") are **not verified** without a configured `SupportJudge`. They are
  labelled `qualitative_unverified`, never `supported`. An LLM entailment judge is the next step and needs its own
  evaluation against human labels.
- Numeric matching requires the dossier to carry structured datapoints. Evidence with text only (most news)
  can't support numbers.
- Injection detection is heuristic. The structural defence is that numbers enter only through gated, bounded
  assumptions. An uncited plausible-looking poisoned assumption still enters that analyst's valuation; it is
  contained by cross-examination and dispersion limits, not blocked (see eval case `injection_uncited`).

## Valuation model
- Annual periods, end-of-year discounting, constant WACC, Gordon terminal value on a normalised steady-state year.
- No NOL carryforwards; tax is on positive EBIT only.
- Power cost scales linearly with utilisation; lease cost per energised MW; leases expensed in opex (so lease
  liabilities are not subtracted in the bridge, and doing both is refused).
- Existing fleet assumed evenly spread across ages 0..2×average age.
- Debt maturities beyond year 3 are not modelled; refinancing occurs at `new_debt_rate`.
- No explicit customer-level contracts, take-or-pay, or backlog conversion schedule. Backlog enters only indirectly
  through `energization_rate`. This is the biggest gap for CoreWeave (see COREWEAVE_PLAN.md).
- Plausibility bounds are typo guards, not views.

## Committee statistics
- The pooled distribution weights analysts equally. With one underlying model, five analysts are not five
  independent opinions; the distribution is not a calibrated probability.
- Scenario probabilities are analyst-asserted. They become meaningful only once scored against outcomes over time
  (Brier score on triggers).
- Conformity detection flags but does not reject. It can't distinguish "persuaded by a good argument without new
  evidence" (legitimate) from social drift.

## Data freshness
- Market prices are whatever the dossier records, with its as-of date. Nothing is real-time. A price older than 5
  days forces ABSTAIN.
- Staleness limits by source kind are configurable defaults, not facts.
