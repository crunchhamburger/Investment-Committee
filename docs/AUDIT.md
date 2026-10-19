# Audit of the original MVP (`ai_investment_committee_mvp.zip`)

Single file `committee.py` (≈220 lines), 4 tests (all pass), README, sample dossier, example output. Findings come
from reading the code and running adversarial probes against it, not from the README's description.

## Ranked weaknesses

| # | Severity | Finding | Evidence |
|---|---|---|---|
| 1 | Critical | **Agents have no causal effect on the decision.** Scenario numbers are fixed in the dossier before any agent runs. The "debate" is one LLM call writing all five voices. No revisions; the veto is a prompt sentence. | `run()`: `values = valuation(dossier)` precedes all LLM calls; single `generate(...)` for debate |
| 2 | Critical | **Citation check verifies only that IDs exist.** | `"Revenue was $9,999 million [E1]"` passes (evidence says $1,000M); `[E1, E42]` parses as zero citations; uncited sentences pass if any other sentence cites |
| 3 | Critical | **SEC extractor understates debt.** It takes the first matching concept, i.e. the current portion. Dossier `as_of` is stamped with today's date. | Mock with $1bn current + $15bn noncurrent → reported "Long-term debt: $1,000M" (94% understated) |
| 4 | High | **Valuation is not a valuation.** Future revenue × multiple vs today's price; no discounting or horizon; dilution claimed but not computed; cash/debt vary by scenario; no bounds. | 500× EV/revenue accepted; −$970/share produced; `True` accepted as revenue |
| 5 | High | **Demo and tests check scripted strings.** AI path untested; no structured outputs, retries, timeouts or cache; raw dossier JSON in prompts (injection); analysts see price and finished valuation before writing (anchoring). | `test_offline_end_to_end` asserts `'ABSTAIN' in chair` where chair is a hardcoded string |

## Worth keeping (and kept)
Refusing to treat missing debt as zero; an explicit synthetic flag; no broker or order path; candid README caveats.

## Disposition
Replaced rather than patched: weakness 1 is architectural. Each weakness has a regression test in
`tests/test_mvp_regressions.py` and/or an adversarial case in `icommittee/eval/harness.py`.
