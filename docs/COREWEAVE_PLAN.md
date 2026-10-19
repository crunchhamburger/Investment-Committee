# CoreWeave (CRWV) as the first real case

No CoreWeave figures are included or assumed here. Every number must enter through the registry from a dated
primary source (10-K/10-Q, earnings release, 8-K, debt agreements) and pass `python -m icommittee check`.

## Your questions, mapped to the model

| Research question | Where it lives now | Gap to close |
|---|---|---|
| How does contracted backlog convert into recognisable revenue? | Indirectly via `energization_rate` × utilisation × price | Add an explicit **backlog conversion schedule**: RPO by expected recognition bucket (disclosed in filings) as a fact, cross-checked against modelled revenue. Flag when modelled revenue exceeds what RPO plus plausible new bookings supports. |
| What limits converting electrical capacity into usable compute? | `energization_rate`, `pue`, `kw_per_gpu` | **Site-level power ramps** (contracted vs active MW by site, with delivery dates) instead of one pooled rate. |
| How do GPU generations affect revenue productivity and depreciation? | `price_decay_per_year_of_age`, `price_new_growth_per_year`, economic vs useful life, write-offs | **Generation mix** (fleet by generation) with generation-specific pricing and kW/GPU. |
| How sensitive is equity value to price and utilisation? | Sensitivity grid, reverse DCF | Done. Add a 3-way (price × utilisation × decay) table. |
| How do financing costs and maturities affect equity returns? | `credit_projection`: refinancing at new rates, coverage, funding gap | **Facility-level debt** (delayed-draw facilities tied to specific contracts, their amortisation and covenants), plus maturities beyond year 3. |
| Who captures the economics? | Cohort IRR vs WACC; funding gap; bridge | Split cash flows explicitly to creditors (interest + amortisation), suppliers (capex), landlords (leases), customers (price concessions) and equity, per cohort. |
| What justifies the current price? | Reverse DCF per driver | Done. Add a multi-driver "implied scenario" solve. |
| What could invalidate the thesis? | Analyst triggers, chair triggers | Store and score triggers quarterly. |

## Dossier checklist (each needs a dated primary source and a page reference)
- Balance sheet at the latest quarter: total debt by facility, cash, lease liabilities, PP&E net.
- Shares: basic, RSUs, options with weighted-average strike, any convertibles or warrants.
- Debt maturities by year (from the debt footnote).
- Contracted and active power (MW), from earnings releases. Watch for later corrections (supersession).
- RPO and the share expected to be recognised within 12 and 24 months.
- Customer concentration (revenue share by major customer).
- Depreciation policy and any useful-life changes.
- Management guidance (capex, revenue, MW), labelled `management_guidance`, never as fact.
- Price with its as-of date (end-of-day; not real-time).
- Secondary: GPU rental pricing surveys, competitor capacity, customer self-build plans. Tag topics so role views
  work, and record `derived_from` for syndicated stories.

## Suggested first committee configuration
- Analysts on at least two different model providers (alternate across seats).
- `ICOMMITTEE_STRICT_GATE=1` for the first real run, so every mislabel is a visible rejection.
- Run `check` until the fact layer has no missing items, before spending on LLM calls.
