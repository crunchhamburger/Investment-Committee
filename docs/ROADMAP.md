# Roadmap

## Done in v0.2 (this rebuild), by priority
1. Evidence registry: versioned, point-in-time, supersession, conflicts, provenance roots, injection flags.
2. Claim verifier with numeric matching and epistemic-basis checks.
3. Assumption gate: facts registry-only, no defaults, bounded, labels enforced, rejected proposals quarantined
   across versions.
4. Driver-based GPU-cloud DCF with a correct EV→equity bridge (intrinsic-price dilution, lease double-count
   guard), credit projection, cohort IRR, reverse DCF, sensitivity.
5. Six-stage pipeline: price-blind stage 1, code-based disagreement attribution, targeted cross-examination,
   audited revisions with conformity detection, rule-based risk veto, constrained chair.
6. LLM layer: OpenAI and Anthropic transports, caching, retries, schema repair, cost log; offline fixtures.
7. SEC extractor that fixes the MVP's debt understatement and date stamping.
8. Eval harness and 104 tests.

## Next (in order)
1. **First live run on a real dossier** with two providers across analysts. Fix whatever schema-compliance and
   prompt issues appear. *Nothing else on this list matters until this works.*
2. **Run the planted-flaw benchmark** (docs/EVALUATION.md), including the 5×-compute single-agent arm. This decides
   whether the committee is worth its cost.
3. **CoreWeave model extensions** (docs/COREWEAVE_PLAN.md): backlog conversion schedule, contract/customer
   concentration as a discrete scenario, site-level power ramps, GPU generation mix, debt-facility-level financing.
4. **LLM support judge** for qualitative claims, evaluated against ~200 human-labelled claim/excerpt pairs.
5. **Dossier tooling**: a CLI to add hand-entered primary datapoints with source page references, since MW,
   maturities and dilution aren't in XBRL.
6. **Trigger and probability scoring** store for calibration over time.

## Can wait
- Browser UI (build only after (1)–(2) show the workflow is worth using).
- Precedent transactions and full comps modules (keep revenue/EBITDA multiples as cross-checks only).
- Shapley attribution (only if interaction residuals are routinely large).
- Quarterly model granularity.
- Multi-round debate (one targeted round first; add rounds only if the benchmark shows a second round finds
  more).

## Candidates for removal
- **Separate credit LLM seat**, if live runs show it adds nothing beyond `credit_projection` plus the risk seat.
- **Conformity flag as a soft signal**: either make it reject (once its false-positive rate is known) or drop it.
  A flag nobody acts on is noise.
- **The committee itself**, if the benchmark shows a single model with equal compute and the same deterministic
  controls finds as many flaws. Most of the reliability in this system comes from the controls, not the number of
  agents.
