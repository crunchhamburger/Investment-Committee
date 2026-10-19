# Evaluation

`python -m icommittee eval` runs everything below offline and writes `committee_output/eval/eval.md`.

## What the offline harness measures

| Dimension | Metric | How |
|---|---|---|
| Factual accuracy | Share of quantitative claims that match a structured datapoint | Claim verifier over all reports |
| Citation validity and support | Verdict distribution; independent-root counts | Claim verifier |
| Control effectiveness | Adversarial catch rate (24 cases) | Fault injection into fixtures and dossiers |
| Valuation consistency | Recompute every stored valuation from stored inputs; check EV, bridge and per-share identities | `valuation_consistency` |
| Disagreement quality | Spread per driver, information asymmetry vs interpretation, interaction residuals | Attribution output |
| Does debate change conclusions? | Accepted/rejected changes, evidence-backed share, conformity flags, Δ base value per analyst, dispersion before/after, top-driver gap before/after | `debate_metrics` |
| Reproducibility | Identical decision fingerprint and valuation hashes across runs | Repeated runs |
| Cost and latency | Calls, cache hits, tokens, cost, latency, retries, repairs | Call log |

## The experiment that answers the guiding question

> Can independently motivated AI researchers identify weaknesses in an investment thesis that a single analyst,
> or a single general-purpose assistant, would otherwise miss?

This needs live models. The offline harness deliberately does **not** report a committee-vs-baseline result,
because a scripted baseline would prove only what the fixture author wrote.

**Protocol (planted-flaw benchmark):**
1. Build 10–20 dossiers from real filings (point-in-time). In each, plant 4–8 material weaknesses that a careful
   analyst should find: concentration buried in a footnote, a useful-life extension, slow backlog conversion, a
   maturity wall, a superseded figure, a guidance number presented as fact, a poisoned secondary source. Record each
   flaw's ID, location and evidence ID. Have a human analyst confirm each is material and findable.
2. Arms, all on the same dossier and evidence:
   - **A. Single generalist**: one call, same output schema, same evidence (all of it).
   - **B. Single generalist, 5× compute**: same model asked to self-critique and revise, roughly matching the
     committee's token budget. *This is the arm that matters:* without it, any committee gain could just be more
     tokens.
   - **C. Committee, same model** for every seat.
   - **D. Committee, mixed models** (e.g. two providers across analysts).
3. Score with `flaw_coverage` (same rubric for every arm), plus human grading of a sample to validate the rubric.
4. Report per arm: flaw recall, false-flaw rate (asserted weaknesses that aren't real), decision changes after
   debate, cost and latency. Run ≥5 seeds per dossier at temperature > 0 and report variance.
5. The proposition is supported only if **C or D beats B** on recall at a similar false-flaw rate, and the gain
   survives human grading. If C ≈ B, the committee is an expensive self-critique loop. Then simplify to one
   generalist plus the deterministic controls, which is where most of the reliability comes from anyway.

**Longer-run calibration:** store every analyst's scenario probabilities and invalidation triggers. Score them
quarterly against what happened (Brier score; trigger hit rate). That's the only honest way to give "confidence"
a meaning.
