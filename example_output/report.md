# Investment Committee: Hypothetical GPU Cloud Co. (DEMO) - SYNTHETIC
> **SYNTHETIC DATA. Not investable.** All evidence and LLM outputs in this run are scripted fixtures. They exercise the pipeline's controls; they are not evidence that the committee works.
Session date **2026-10-09** · registry snapshot `dee5f55a7f7ab261` · price: $45.00 (Fixture exchange feed, as of 2026-10-08). Prices are end-of-day as recorded in the registry, not real-time.

## Decision
**HOLD**

| Valuation p10 | Probability-weighted | p90 | Price | Expected return | Position size |
|---|---|---|---|---|---|
| $0.00 | $42.55 | $71.47 | $45.00 | -5.5% | none |

Why: probability-weighted value 42.55 vs price 45.00 (expected return -5.5%, hurdle 15%)

Sizing basis: min(max_position 5%, loss_budget 1.0% / median bear drawdown); NAV-relative; ignores correlation with the rest of the portfolio.

**Process flags:** `consensus_cited_as_support: analyst agreement is not independent evidence`; `synthetic_data: not investable`; `decision_held_by_no_analyst: the committee view is an average of positions nobody holds; read the dissent table, not the headline`

**Primary thesis.** SCRIPTED FIXTURE. Value depends on GPU-hour pricing holding up as the fleet ages; the pricing survey (EV-005) and the 2024 useful-life extension (EV-009) suggest reported earnings overstate sustainable cash generation.

**Strongest opposing thesis.** Contracted power of 2.5 GW against 0.9 GW energised (EV-013) and management's $3.00 contracted pricing (EV-003) could support rapid growth if energisation accelerates.

**Catalysts**
- Q3 energised MW versus the 1.6 GW dark backlog
- Repricing of the next large contract renewal
- Refinancing of the $4.0bn year-2 maturity (EV-001)

**Key risks**
- The majority of analysts agree pricing decay is underappreciated.
- 60% customer concentration (EV-001).
- Single-customer concentration (60% of revenue) is not modelled as a discrete event.
- Contract cancellability is unknown; take-or-pay terms would change the bear case materially.
- Maturities beyond 36 months are not in the dossier, so refinancing risk is understated.

**Unresolved questions**
- What share of revenue is on take-or-pay contracts?
- Economic life of current GPUs?

**Reconsideration triggers**
- Energised MW exceeds 1,400 by mid-2027 (`active_power_mw > 1400 MW`)
- Prior-generation pricing stabilises above $2.50 (`gpu_hour_price_prior_gen > 2.5 USD_per_hour`)

### Dissent (preserved, not averaged away)
| Analyst | Expected value/share | Implied view | Thesis |
|---|---|---|---|
| value | $37.67 | sell | Reported earnings overstate the economics: maintenance capex on a six-year accounting life with a shorter economic life leaves little free cash flow for equity after debt service. No margin of safety at $45. |
| growth | $60.85 | buy | Contracted power of 2.5 GW against 0.9 GW energised is a multi-year revenue runway; at management's $3.00 contracted pricing the build-out compounds equity value. |
| credit | $52.98 | buy | The enterprise can grow, but equity holders capture little of it: refinancing $9bn of maturities over three years at higher rates and funding 30% of capex internally leaves coverage adequate but thin. |
| industry | $25.09 | sell | Prior-generation pricing has fallen roughly 30% in a year and the largest customer is building its own capacity; installed-fleet revenue productivity will decay faster than management implies. |
| contrarian | $36.14 | sell | The market treats the 2.5 GW contracted figure as revenue in waiting. Only 40% of RPO converts within 24 months and one customer is 60% of revenue; the real constraint is energisation pace, not demand. |

## Risk review
Veto: **YES** · P(impairment): 39.0% · analyst dispersion: 70.0%

| Rule | Metric | Observed | Threshold | Pass | Action |
|---|---|---|---|---|---|
| min_interest_coverage | EBITDA / interest, worst year (median-assumption case) | 4.229 | 1.5 | ✓ | veto |
| max_net_debt_to_ebitda | peak net debt / EBITDA (median-assumption case) | 2.060 | 6 | ✓ | warn |
| max_prob_impairment | P(value < price x 0.70) | 0.390 | 0.35 | ✗ | veto |
| max_bear_drawdown | 1 - median bear value / price | 1.000 | 0.6 | ✗ | cap_size |
| max_model_dispersion | (p90 - p10) / median of analysts' base values | 0.700 | 1.5 | ✓ | warn |
| max_terminal_share | median terminal value share of EV | 0.863 | 0.85 | ✗ | warn |

SCRIPTED FIXTURE. Coverage and leverage limits pass in the median-assumption case, but the pooled distribution places substantial weight on equity being impaired: the equity is a levered call on utilization and pricing. Cohort economics are positive but thin relative to the cost of capital.

Risks outside the model:
- Single-customer concentration (60% of revenue) is not modelled as a discrete event.
- Contract cancellability is unknown; take-or-pay terms would change the bear case materially.
- Maturities beyond 36 months are not in the dossier, so refinancing risk is understated.

## Disagreements that move value
Reference (median-assumption) value: $58.29/share (unfloored).

| Driver | Spread $/share | Low | High | Kind | Note |
|---|---|---|---|---|---|
| price_decay_per_year_of_age | 43.30 | industry (0.16) | growth (0.11) | information_asymmetry | one side cites evidence the other side did not see |
| utilization | 38.51 | contrarian (0.8) | growth (0.88) | assumption |  |
| wacc | 12.61 | credit (0.115) | growth (0.105) | assumption |  |

Interaction residuals (gap not explained by one-at-a-time swaps): contrarian +1.32, credit -1.67, growth +8.27, industry +0.42, value +2.38

## Cross-examination
- **contrarian->growth:utilization**: 60% of revenue comes from one customer that is building 1 GW of its own capacity. Why is 88% utilization durable through 2028? *(counter 0.8)* [EV-001, EV-006]
  - Response (holds): Concentration is real, but the self-build is a 2028 event and current contracts run multiple years. I keep 88% for the base case and lower the bear case.
- **credit->growth:wacc**: New unsecured notes priced at 9.25% with a 4.3% 10-year Treasury. How is 10.5% a cost of capital for the equity-heavy marginal dollar? [EV-008, EV-014]
  - Response (holds): The 9.25% coupon is a debt cost; with ~50% debt weighting 10.5% is defensible.
- **growth->industry:price_decay_per_year_of_age**: Most of the fleet is on multi-year contracts at about $3.00. Does a spot-market survey describe contracted revenue at all? [EV-003]
  - Response (holds): Contract terms are not disclosed in the dossier, so the share of the fleet protected from spot pricing is unknown. Survey-based decay remains the best available evidence.
- **growth->contrarian:utilization**: Management reports fleet utilization above 90%. What evidence supports 80%? *(counter 0.9)* [EV-003]
  - Response (concedes): Management's >90% is unaudited guidance, but it is evidence I had ignored. I move partway.
- **growth->credit:wacc**: Isn't 11.5% too punitive for a business with $55bn of contracted backlog? [no evidence cited]
  - Response (holds): Backlog does not lower the cost of capital if it is concentrated in one counterparty.
- **industry->growth:price_decay_per_year_of_age**: The September survey shows prior-generation prices falling 15-20% per year of age and H100-class pricing down ~30% y/y. What evidence supports your 11%? *(counter 0.175)* [EV-005]
  - Response (concedes): I had not seen the pricing survey. Contracted pricing softens the effect but 11% is too low; I will move toward the survey range.

## Belief revision
| Analyst | Scenario | Driver | Old → New | Accepted | Flags | Basis |
|---|---|---|---|---|---|---|
| value | base | utilization | 0.83 → 0.86 | **no** | no_basis | - |
| growth | base | price_decay_per_year_of_age | 0.11 → 0.15 | yes | - | industry->growth:price_decay_per_year_of_age, EV-005 |
| growth | bull | energization_rate | 0.4 → 0.5 | yes | - | EV-003 |
| growth | bear | utilization | 0.8 → 0.75 | yes | - | contrarian->growth:utilization, EV-001 |
| credit | base | wacc | 0.115 → 0.108 | yes | conformity_suspect: moved toward committee median without new evidence | growth->credit:wacc |
| industry | - | - | retained | - | - | Growth's challenge relies on undisclosed contract terms; the survey remains the best evidence. |
| contrarian | base | utilization | 0.8 → 0.83 | yes | - | growth->contrarian:utilization, EV-003 |

| Analyst | Base before | Base after | Expected before | Expected after |
|---|---|---|---|---|
| value | 38.78 | 38.78 | 37.67 | 37.67 |
| growth | 111.14 | 67.47 | n/a | 60.85 |
| credit | 57.72 | 67.00 | 48.34 | 52.98 |
| industry | 26.23 | 26.23 | 25.09 | 25.09 |
| contrarian | 38.02 | 51.47 | 30.09 | 36.14 |

## Analyst reports (final versions)

### value (v2, model `fixture`): negative
Reported earnings overstate the economics: maintenance capex on a six-year accounting life with a shorter economic life leaves little free cash flow for equity after debt service. No margin of safety at $45.

Value/share: bear 0.00 · base 38.78 · bull 91.42 · expected 37.67

| Claim | Label | Verdict | Detail |
|---|---|---|---|
| Total debt was $20.0bn at June 30, 2026. | verified_fact | **supported** | matched structured datapoint |
| Fleet utilization is 92%. | verified_fact | **basis_mismatch** | claim labelled verified_fact but source labels it ['management_guidance'] |
| GPU servers are depreciated over six years. | verified_fact | **stale_source** | matched structured datapoint |
| If economic life is shorter than the accounting life, reported EBIT overstates sustainable earnings. | analyst_assumption | **not_applicable** | analyst_assumption: no external support claimed |

<details><summary>Base-case drivers and model rows</summary>

| Driver | Value | Label | Rationale |
|---|---|---|---|
| capex_per_gpu | 40000 | analyst_assumption | All-in server, networking and installation cost per GPU. |
| debt_funded_share_of_capex | 0.7 | analyst_assumption | Historical financing mix of asset-backed and unsecured debt. |
| energization_rate | 0.35 | analyst_assumption | Share of the contracted-but-dark backlog brought online each year. |
| existing_fleet_avg_age | 1 | analyst_assumption | Fleet was largely deployed over the last two years. |
| existing_ppe_remaining_life | 5 | analyst_assumption | Remaining depreciation life of the installed base. |
| gpu_economic_life_years | 6 | analyst_assumption | Expected service life before replacement. |
| gpu_useful_life_years | 6 | analyst_assumption | Company's stated accounting life. |
| kw_per_gpu | 1.4 | analyst_assumption | All-in IT load per GPU for current-generation racks including networking. |
| lease_cost_per_mw_year | 1.2e+06 | analyst_assumption | Colocation lease cost per energised MW. |
| mw_additions_per_year | 400 | analyst_assumption | Pace of new contracted capacity. |
| new_debt_rate | 0.085 | analyst_assumption | Recent issuance levels for comparable high-yield infrastructure credits. |
| nwc_pct_revenue_change | 0.05 | analyst_assumption | Customer prepayments partly offset receivables. |
| other_opex_pct_revenue | 0.12 | analyst_assumption | Staffing, network, SG&A as share of revenue. |
| power_cost_per_mwh | 65 | analyst_assumption | Blended industrial power contracts in the company's regions. |
| price_decay_per_year_of_age | 0.13 | analyst_assumption | Discount per year of hardware age as new generations arrive. |
| price_new_growth_per_year | 0 | analyst_assumption | Newest-generation pricing assumed flat in nominal terms. |
| price_per_gpu_hour_new | 2.95 | analyst_assumption | Blended price per GPU-hour for newest generation. |
| pue | 1.3 | analyst_assumption | Modern liquid-cooled halls; 1.3 is a typical design PUE. |
| tax_rate | 0.21 | analyst_assumption | Statutory rate; NOLs ignored for simplicity. |
| terminal_growth | 0.02 | analyst_assumption | Long-run nominal growth after the build-out phase. |
| utilization | 0.83 | analyst_assumption | Haircut to management's >90% claim, which is unaudited. |
| wacc | 0.11 | analyst_assumption | Levered equity with refinancing needs warrants a higher discount rate. |

| Yr | Energised MW | GPUs (k) | Revenue | EBITDA | Capex | FCFF |
|---|---|---|---|---|---|---|
| 1 | 1,460 | 802 | $14.7bn | $10.5bn | $12.3bn | $-2.8bn |
| 2 | 1,964 | 1,079 | $18.7bn | $13.2bn | $11.1bn | $1.0bn |
| 3 | 2,432 | 1,336 | $21.8bn | $15.1bn | $10.3bn | $3.7bn |
| 4 | 2,876 | 1,580 | $26.2bn | $18.2bn | $16.4bn | $0.6bn |
| 5 | 3,304 | 1,815 | $29.8bn | $20.7bn | $16.0bn | $3.5bn |
| 6 | 3,723 | 2,045 | $32.9bn | $22.7bn | $15.8bn | $4.9bn |

EV $39.7bn + cash $2.0bn − debt $20.0bn − leases $0.0bn (treatment: opex) − preferred $0.0bn − minority $0.0bn = equity $21.7bn; diluted shares 559.7m → $38.78. Terminal value is 84.6% of EV. Inputs hash `34e0dbb2b9561420`.

</details>

### growth (v2, model `fixture`): positive
Contracted power of 2.5 GW against 0.9 GW energised is a multi-year revenue runway; at management's $3.00 contracted pricing the build-out compounds equity value.

Value/share: bear 0.00 · base 67.47 · bull 90.37 · expected 60.85

| Claim | Label | Verdict | Detail |
|---|---|---|---|
| Management targets 400-600 MW of new contracted power per year. | management_guidance | **supported** | matched structured datapoint |
| Active power reached 950 MW at quarter end. | verified_fact | **superseded_source** | ['EV-002'] superseded by ['EV-013'] |
| Remaining performance obligations were $75bn. | verified_fact | **value_mismatch** | claimed 7.5e+10; sources say EV-001=5.5e+10 |
| New-generation clusters are contracted at about $3.00 per GPU-hour. | management_guidance | **supported** | matched structured datapoint |
| Active power was 900 MW at quarter end (corrected release). | verified_fact | **supported** | matched structured datapoint |

<details><summary>Base-case drivers and model rows</summary>

| Driver | Value | Label | Rationale |
|---|---|---|---|
| capex_per_gpu | 40000 | analyst_assumption | All-in server, networking and installation cost per GPU. |
| debt_funded_share_of_capex | 0.7 | analyst_assumption | Historical financing mix of asset-backed and unsecured debt. |
| energization_rate | 0.4 | analyst_assumption | Power is contracted; energisation is an execution question. |
| existing_fleet_avg_age | 1 | analyst_assumption | Fleet was largely deployed over the last two years. |
| existing_ppe_remaining_life | 5 | analyst_assumption | Remaining depreciation life of the installed base. |
| gpu_economic_life_years | 6 | analyst_assumption | Expected service life before replacement. |
| gpu_useful_life_years | 6 | analyst_assumption | Company's stated accounting life. |
| kw_per_gpu | 1.4 | analyst_assumption | All-in IT load per GPU for current-generation racks including networking. |
| lease_cost_per_mw_year | 1.2e+06 | analyst_assumption | Colocation lease cost per energised MW. |
| mw_additions_per_year | 550 | analyst_assumption | Upper half of management's range given demand. |
| new_debt_rate | 0.085 | analyst_assumption | Recent issuance levels for comparable high-yield infrastructure credits. |
| nwc_pct_revenue_change | 0.05 | analyst_assumption | Customer prepayments partly offset receivables. |
| other_opex_pct_revenue | 0.12 | analyst_assumption | Staffing, network, SG&A as share of revenue. |
| power_cost_per_mwh | 65 | analyst_assumption | Blended industrial power contracts in the company's regions. |
| price_decay_per_year_of_age | 0.15 | analyst_assumption | Pricing survey shows 15-20% decline per year of age; contracted pricing justifies the low end. |
| price_new_growth_per_year | 0 | analyst_assumption | Newest-generation pricing assumed flat in nominal terms. |
| price_per_gpu_hour_new | 3 | management_guidance | Management's contracted price. |
| pue | 1.3 | analyst_assumption | Modern liquid-cooled halls; 1.3 is a typical design PUE. |
| tax_rate | 0.21 | analyst_assumption | Statutory rate; NOLs ignored for simplicity. |
| terminal_growth | 0.03 | analyst_assumption | Long-run nominal growth after the build-out phase. |
| utilization | 0.88 | analyst_assumption | Share of GPU-hours sold across the fleet. |
| wacc | 0.105 | analyst_assumption | High-beta, highly levered equity; cost of capital set conservatively. |

| Yr | Energised MW | GPUs (k) | Revenue | EBITDA | Capex | FCFF |
|---|---|---|---|---|---|---|
| 1 | 1,540 | 846 | $16.5bn | $11.9bn | $14.1bn | $-3.5bn |
| 2 | 2,144 | 1,178 | $21.7bn | $15.4bn | $13.3bn | $0.7bn |
| 3 | 2,726 | 1,498 | $25.8bn | $18.1bn | $12.8bn | $3.7bn |
| 4 | 3,296 | 1,811 | $31.6bn | $22.2bn | $19.1bn | $1.2bn |
| 5 | 3,858 | 2,120 | $36.3bn | $25.4bn | $18.9bn | $4.7bn |
| 6 | 4,415 | 2,426 | $40.3bn | $28.0bn | $18.8bn | $6.5bn |

EV $56.1bn + cash $2.0bn − debt $20.0bn − leases $0.0bn (treatment: opex) − preferred $0.0bn − minority $0.0bn = equity $38.1bn; diluted shares 564.1m → $67.47. Terminal value is 86.8% of EV. Inputs hash `f4a78fa9d31ecd43`.

- ⚠ terminal value is 87% of EV: valuation is mostly a perpetuity assumption

</details>

### credit (v2, model `fixture`): neutral
The enterprise can grow, but equity holders capture little of it: refinancing $9bn of maturities over three years at higher rates and funding 30% of capex internally leaves coverage adequate but thin.

Value/share: bear 17.29 · base 67.00 · bull 71.47 · expected 52.98

| Claim | Label | Verdict | Detail |
|---|---|---|---|
| Weighted average interest rate on debt was 9.0%. | verified_fact | **supported** | matched structured datapoint |
| Recent senior notes priced at a 9.25% coupon. | verified_fact | **basis_mismatch** | verified facts need at least one primary source |
| $4.0bn of debt matures in months 13-24. | verified_fact | **supported** | matched structured datapoint |
| Lease liabilities were $15.0bn. | verified_fact | **supported** | matched structured datapoint |

<details><summary>Base-case drivers and model rows</summary>

| Driver | Value | Label | Rationale |
|---|---|---|---|
| capex_per_gpu | 40000 | analyst_assumption | All-in server, networking and installation cost per GPU. |
| debt_funded_share_of_capex | 0.7 | analyst_assumption | Historical financing mix of asset-backed and unsecured debt. |
| energization_rate | 0.35 | analyst_assumption | Share of the contracted-but-dark backlog brought online each year. |
| existing_fleet_avg_age | 1 | analyst_assumption | Fleet was largely deployed over the last two years. |
| existing_ppe_remaining_life | 5 | analyst_assumption | Remaining depreciation life of the installed base. |
| gpu_economic_life_years | 6 | analyst_assumption | Expected service life before replacement. |
| gpu_useful_life_years | 6 | analyst_assumption | Company's stated accounting life. |
| kw_per_gpu | 1.4 | analyst_assumption | All-in IT load per GPU for current-generation racks including networking. |
| lease_cost_per_mw_year | 1.2e+06 | analyst_assumption | Colocation lease cost per energised MW. |
| mw_additions_per_year | 450 | analyst_assumption | Pace of new contracted capacity. |
| new_debt_rate | 0.095 | analyst_assumption | Recent 9.25% notes plus a modest premium for refinancing size. |
| nwc_pct_revenue_change | 0.05 | analyst_assumption | Customer prepayments partly offset receivables. |
| other_opex_pct_revenue | 0.12 | analyst_assumption | Staffing, network, SG&A as share of revenue. |
| power_cost_per_mwh | 65 | analyst_assumption | Blended industrial power contracts in the company's regions. |
| price_decay_per_year_of_age | 0.12 | analyst_assumption | Discount per year of hardware age as new generations arrive. |
| price_new_growth_per_year | 0 | analyst_assumption | Newest-generation pricing assumed flat in nominal terms. |
| price_per_gpu_hour_new | 3 | analyst_assumption | Blended price per GPU-hour for newest generation. |
| pue | 1.3 | analyst_assumption | Modern liquid-cooled halls; 1.3 is a typical design PUE. |
| tax_rate | 0.21 | analyst_assumption | Statutory rate; NOLs ignored for simplicity. |
| terminal_growth | 0.02 | analyst_assumption | Long-run nominal growth after the build-out phase. |
| utilization | 0.85 | analyst_assumption | Share of GPU-hours sold across the fleet. |
| wacc | 0.108 | analyst_assumption | On reflection the growth analyst's point about backlog has some merit. |

| Yr | Energised MW | GPUs (k) | Revenue | EBITDA | Capex | FCFF |
|---|---|---|---|---|---|---|
| 1 | 1,460 | 802 | $15.5bn | $11.2bn | $12.3bn | $-2.3bn |
| 2 | 1,982 | 1,089 | $20.0bn | $14.3bn | $11.5bn | $1.5bn |
| 3 | 2,478 | 1,362 | $23.7bn | $16.7bn | $10.9bn | $4.4bn |
| 4 | 2,958 | 1,625 | $28.7bn | $20.3bn | $17.1bn | $1.5bn |
| 5 | 3,428 | 1,883 | $33.0bn | $23.3bn | $16.9bn | $4.7bn |
| 6 | 3,891 | 2,138 | $36.7bn | $25.8bn | $16.8bn | $6.4bn |

EV $55.8bn + cash $2.0bn − debt $20.0bn − leases $0.0bn (treatment: opex) − preferred $0.0bn − minority $0.0bn = equity $37.8bn; diluted shares 564.0m → $67.00. Terminal value is 82.8% of EV. Inputs hash `b4b0245bb4b2ab8c`.

</details>

### industry (v2, model `fixture`): negative
Prior-generation pricing has fallen roughly 30% in a year and the largest customer is building its own capacity; installed-fleet revenue productivity will decay faster than management implies.

Value/share: bear 0.00 · base 26.23 · bull 59.86 · expected 25.09

| Claim | Label | Verdict | Detail |
|---|---|---|---|
| Median prior-generation pricing is $2.20 per GPU-hour. | third_party_estimate | **supported** | matched structured datapoint |
| Prices decline about 17.5% per year of hardware age. | third_party_estimate | **supported** | matched structured datapoint |
| The largest customer plans to bring 1 GW of self-built capacity online by 2028. | third_party_estimate | **unstructured_number** | claim states a number in prose without structured metric/value; restate it as a quantitative claim so it can be checked |

<details><summary>Base-case drivers and model rows</summary>

| Driver | Value | Label | Rationale |
|---|---|---|---|
| capex_per_gpu | 40000 | analyst_assumption | All-in server, networking and installation cost per GPU. |
| debt_funded_share_of_capex | 0.7 | analyst_assumption | Historical financing mix of asset-backed and unsecured debt. |
| energization_rate | 0.35 | analyst_assumption | Share of the contracted-but-dark backlog brought online each year. |
| existing_fleet_avg_age | 1 | analyst_assumption | Fleet was largely deployed over the last two years. |
| existing_ppe_remaining_life | 5 | analyst_assumption | Remaining depreciation life of the installed base. |
| gpu_economic_life_years | 6 | analyst_assumption | Expected service life before replacement. |
| gpu_useful_life_years | 6 | analyst_assumption | Company's stated accounting life. |
| kw_per_gpu | 1.4 | analyst_assumption | All-in IT load per GPU for current-generation racks including networking. |
| lease_cost_per_mw_year | 1.2e+06 | analyst_assumption | Colocation lease cost per energised MW. |
| mw_additions_per_year | 450 | analyst_assumption | Pace of new contracted capacity. |
| new_debt_rate | 0.085 | analyst_assumption | Recent issuance levels for comparable high-yield infrastructure credits. |
| nwc_pct_revenue_change | 0.05 | analyst_assumption | Customer prepayments partly offset receivables. |
| other_opex_pct_revenue | 0.12 | analyst_assumption | Staffing, network, SG&A as share of revenue. |
| power_cost_per_mwh | 65 | analyst_assumption | Blended industrial power contracts in the company's regions. |
| price_decay_per_year_of_age | 0.16 | analyst_assumption | Slightly below the survey's 17.5% because part of the fleet is on fixed-price contracts. |
| price_new_growth_per_year | 0 | analyst_assumption | Newest-generation pricing assumed flat in nominal terms. |
| price_per_gpu_hour_new | 2.95 | analyst_assumption | Blended price per GPU-hour for newest generation. |
| pue | 1.3 | analyst_assumption | Modern liquid-cooled halls; 1.3 is a typical design PUE. |
| tax_rate | 0.21 | analyst_assumption | Statutory rate; NOLs ignored for simplicity. |
| terminal_growth | 0.025 | analyst_assumption | Long-run nominal growth after the build-out phase. |
| utilization | 0.84 | analyst_assumption | Share of GPU-hours sold across the fleet. |
| wacc | 0.105 | analyst_assumption | High-beta, highly levered equity; cost of capital set conservatively. |

| Yr | Energised MW | GPUs (k) | Revenue | EBITDA | Capex | FCFF |
|---|---|---|---|---|---|---|
| 1 | 1,460 | 802 | $14.3bn | $10.2bn | $12.3bn | $-3.1bn |
| 2 | 1,982 | 1,089 | $18.3bn | $12.7bn | $11.5bn | $0.3bn |
| 3 | 2,478 | 1,362 | $21.3bn | $14.5bn | $10.9bn | $2.7bn |
| 4 | 2,958 | 1,625 | $25.9bn | $17.8bn | $17.1bn | $-0.4bn |
| 5 | 3,428 | 1,883 | $29.7bn | $20.4bn | $16.9bn | $2.4bn |
| 6 | 3,891 | 2,138 | $32.8bn | $22.3bn | $16.8bn | $3.7bn |

EV $32.5bn + cash $2.0bn − debt $20.0bn − leases $0.0bn (treatment: opex) − preferred $0.0bn − minority $0.0bn = equity $14.5bn; diluted shares 554.7m → $26.23. Terminal value is 91.7% of EV. Inputs hash `9e3c8f65f4de05a8`.

- ⚠ terminal value is 92% of EV: valuation is mostly a perpetuity assumption

</details>

### contrarian (v2, model `fixture`): negative
The market treats the 2.5 GW contracted figure as revenue in waiting. Only 40% of RPO converts within 24 months and one customer is 60% of revenue; the real constraint is energisation pace, not demand.

Value/share: bear 0.00 · base 51.47 · bull 64.92 · expected 36.14

| Claim | Label | Verdict | Detail |
|---|---|---|---|
| One customer accounted for 60% of quarterly revenue. | verified_fact | **supported** | matched structured datapoint |
| The 2024 useful-life extension reduced depreciation by $1.1bn. | verified_fact | **stale_source** | matched structured datapoint |
| About 40% of RPO is expected to be recognised within 24 months. | verified_fact | **supported** | matched structured datapoint |
| Some commentary claims industry utilization is at 100%. | speculation | **flagged_source** | cites evidence flagged for instruction-like content: ['EV-010']; needs human review before it can support a number |

<details><summary>Base-case drivers and model rows</summary>

| Driver | Value | Label | Rationale |
|---|---|---|---|
| capex_per_gpu | 40000 | analyst_assumption | All-in server, networking and installation cost per GPU. |
| debt_funded_share_of_capex | 0.7 | analyst_assumption | Historical financing mix of asset-backed and unsecured debt. |
| energization_rate | 0.28 | analyst_assumption | Slow RPO conversion (40% in 24 months) implies energisation well below backlog pace. |
| existing_fleet_avg_age | 1 | analyst_assumption | Fleet was largely deployed over the last two years. |
| existing_ppe_remaining_life | 5 | analyst_assumption | Remaining depreciation life of the installed base. |
| gpu_economic_life_years | 6 | analyst_assumption | Expected service life before replacement. |
| gpu_useful_life_years | 6 | analyst_assumption | Company's stated accounting life. |
| kw_per_gpu | 1.4 | analyst_assumption | All-in IT load per GPU for current-generation racks including networking. |
| lease_cost_per_mw_year | 1.2e+06 | analyst_assumption | Colocation lease cost per energised MW. |
| mw_additions_per_year | 450 | analyst_assumption | Pace of new contracted capacity. |
| new_debt_rate | 0.085 | analyst_assumption | Recent issuance levels for comparable high-yield infrastructure credits. |
| nwc_pct_revenue_change | 0.05 | analyst_assumption | Customer prepayments partly offset receivables. |
| other_opex_pct_revenue | 0.12 | analyst_assumption | Staffing, network, SG&A as share of revenue. |
| power_cost_per_mwh | 65 | analyst_assumption | Blended industrial power contracts in the company's regions. |
| price_decay_per_year_of_age | 0.13 | analyst_assumption | Discount per year of hardware age as new generations arrive. |
| price_new_growth_per_year | 0 | analyst_assumption | Newest-generation pricing assumed flat in nominal terms. |
| price_per_gpu_hour_new | 3 | analyst_assumption | Blended price per GPU-hour for newest generation. |
| pue | 1.3 | analyst_assumption | Modern liquid-cooled halls; 1.3 is a typical design PUE. |
| tax_rate | 0.21 | analyst_assumption | Statutory rate; NOLs ignored for simplicity. |
| terminal_growth | 0.025 | analyst_assumption | Long-run nominal growth after the build-out phase. |
| utilization | 0.83 | analyst_assumption | Management's unaudited >90% claim is weak evidence but not zero; moving partway. |
| wacc | 0.105 | analyst_assumption | High-beta, highly levered equity; cost of capital set conservatively. |

| Yr | Energised MW | GPUs (k) | Revenue | EBITDA | Capex | FCFF |
|---|---|---|---|---|---|---|
| 1 | 1,348 | 741 | $13.6bn | $9.7bn | $9.8bn | $-1.0bn |
| 2 | 1,797 | 987 | $17.2bn | $12.1bn | $9.9bn | $1.3bn |
| 3 | 2,246 | 1,234 | $20.3bn | $14.1bn | $9.9bn | $3.2bn |
| 4 | 2,695 | 1,481 | $25.1bn | $17.6bn | $16.5bn | $-0.1bn |
| 5 | 3,144 | 1,728 | $29.3bn | $20.5bn | $16.5bn | $2.8bn |
| 6 | 3,594 | 1,975 | $32.9bn | $22.9bn | $16.5bn | $4.2bn |

EV $46.9bn + cash $2.0bn − debt $20.0bn − leases $0.0bn (treatment: opex) − preferred $0.0bn − minority $0.0bn = equity $28.9bn; diluted shares 562.2m → $51.47. Terminal value is 86.3% of EV. Inputs hash `48828f78f47f24e3`.

- ⚠ terminal value is 86% of EV: valuation is mostly a perpetuity assumption

</details>

## Diagnostics
**What the price implies** (one driver at a time, others at committee median):

| Driver | Median assumption | Value that justifies price |
|---|---|---|
| price_per_gpu_hour_new | 3 | 2.907 |
| utilization | 0.84 | 0.8124 |
| capex_per_gpu | 40000 | 4.206e+04 |
| wacc | 0.105 | 0.1156 |
| energization_rate | 0.35 | 0.1422 |

**GPU cohort economics** (median case, pre-tax, unlevered): capex $40,000, year-1 contribution $16,372, IRR 20.2%, NPV at WACC $9,863, payback 2.8 years.

**Credit (median case):** min coverage 4.23x, peak net debt/EBITDA 2.06x, external funding needed beyond cash $0.0bn, refinanced at new rates $9.0bn.

**Value per share: utilization (rows) × newest-gen $/GPU-hour (columns)**

| util \ price | 2.1 | 2.55 | 3 | 3.45 | 3.9 |
|---|---|---|---|---|---|
| 0.69 | 0.00 | 0.00 | 0.00 | 39.04 | 92.00 |
| 0.765 | 0.00 | 0.00 | 22.19 | 80.90 | 139.61 |
| 0.84 | 0.00 | 0.00 | 58.29 | 122.76 | 187.23 |
| 0.915 | 0.00 | 24.17 | 94.39 | 164.62 | 234.84 |

## Evidence registry
| ID | Title | Tier | Kind | Published | As of | Status | Flags |
|---|---|---|---|---|---|---|---|
| EV-001 | Form 10-Q, quarter ended June 30, 2026 (SYNTHETIC) | primary | sec_filing | 2026-08-10 | 2026-06-30 | active | - |
| EV-002 | Q2 2026 earnings release (original) (SYNTHETIC) | primary | earnings_release | 2026-08-10 | 2026-06-30 | superseded | - |
| EV-013 | Q2 2026 earnings release - correction (SYNTHETIC) | primary | earnings_release | 2026-08-20 | 2026-06-30 | active | - |
| EV-003 | Investor day presentation (SYNTHETIC) | primary | investor_presentation | 2026-09-15 | 2026-09-15 | active | - |
| EV-004 | Closing price (SYNTHETIC) | primary | market_data | 2026-10-08 | 2026-10-08 | active | - |
| EV-005 | GPU rental price survey, September 2026 (SYNTHETIC) | secondary | industry_research | 2026-09-28 | 2026-09-30 | active | - |
| EV-006 | Report: largest customer expanding own data-centre build (SYNTHETIC) | secondary | news | 2026-09-20 | 2026-09-20 | active | - |
| EV-007 | Syndicated: largest customer to self-build (SYNTHETIC) | secondary | news | 2026-09-21 | 2026-09-20 | active | - |
| EV-008 | Company prices $3bn senior notes (SYNTHETIC) | secondary | news | 2026-09-05 | 2026-09-05 | active | - |
| EV-009 | Form 10-K 2025, accounting policies note (SYNTHETIC) | primary | sec_filing | 2026-03-02 | 2025-12-31 | stale | - |
| EV-010 | Blog: why GPU clouds will win (SYNTHETIC) | secondary | news | 2026-09-25 | 2026-09-25 | active | possible_injection |
| EV-014 | US Treasury 10-year yield (SYNTHETIC) | primary | macro | 2026-10-02 | 2026-10-01 | active | - |
| EV-015 | Q3 2026 earnings release (SYNTHETIC, published after session date) | primary | earnings_release | 2026-11-12 | 2026-09-30 | future | - |

Starting-position facts used by every analyst: `contracted_power_mw_0`=2,500, `energized_power_mw_0`=900, `gross_debt_0`=2e+10, `cash_0`=2e+09, `lease_liabilities_0`=1.5e+10, `preferred_0`=0, `minority_interest_0`=0, `existing_ppe_net_0`=2.5e+10, `basic_shares_0`=5e+08, `rsus_0`=3e+07, `options_0`=4e+07, `options_strike`=10, `avg_interest_rate_0`=0.09, `debt_maturity_y1`=2e+09, `debt_maturity_y2`=4e+09, `debt_maturity_y3`=3e+09

## Process integrity
Claim verdicts (final reports): basis_mismatch 2, flagged_source 1, not_applicable 1, stale_source 2, superseded_source 1, supported 11, unstructured_number 1, value_mismatch 1

Assumptions rejected at the gate (initial reports): 1

⚠ **All five analysts use the same model** (`fixture`). Their errors are correlated; treat agreement as one opinion, not five. Configure different providers per role to reduce this.

LLM calls: 20 (cache hits 0, retries 0, schema repairs 0), tokens in/out 39,943/9,357, cost n/a (no pricing configured), latency 0.004s.

## Limitations
See `docs/LIMITATIONS.md`. Key ones: one-at-a-time attribution ignores interactions (residuals shown above); equal analyst weighting is not a calibrated probability; qualitative claims are not verified without a support judge; the model is annual with a constant WACC.
