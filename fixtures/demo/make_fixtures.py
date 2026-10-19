"""Generates the stage-1 analyst fixtures. Run from the project root.
Fixture content is SYNTHETIC and scripted: it exercises the pipeline's
mechanics and checks; it is not evidence that LLM debate works."""
import json
from pathlib import Path

OUT = Path(__file__).parent / "llm"
REF = dict(mw_additions_per_year=450, energization_rate=0.35, pue=1.3, kw_per_gpu=1.4, existing_fleet_avg_age=1,
           utilization=0.85, price_per_gpu_hour_new=3.0, price_new_growth_per_year=0.0, price_decay_per_year_of_age=0.12,
           power_cost_per_mwh=65, lease_cost_per_mw_year=1.2e6, other_opex_pct_revenue=0.12, capex_per_gpu=40000,
           gpu_useful_life_years=6, gpu_economic_life_years=6, existing_ppe_remaining_life=5, tax_rate=0.21,
           nwc_pct_revenue_change=0.05, wacc=0.105, terminal_growth=0.025, debt_funded_share_of_capex=0.7,
           new_debt_rate=0.085)
GENERIC = {
    "pue": "Modern liquid-cooled halls; 1.3 is a typical design PUE.",
    "kw_per_gpu": "All-in IT load per GPU for current-generation racks including networking.",
    "existing_fleet_avg_age": "Fleet was largely deployed over the last two years.",
    "power_cost_per_mwh": "Blended industrial power contracts in the company's regions.",
    "lease_cost_per_mw_year": "Colocation lease cost per energised MW.",
    "other_opex_pct_revenue": "Staffing, network, SG&A as share of revenue.",
    "capex_per_gpu": "All-in server, networking and installation cost per GPU.",
    "gpu_useful_life_years": "Company's stated accounting life.",
    "gpu_economic_life_years": "Expected service life before replacement.",
    "existing_ppe_remaining_life": "Remaining depreciation life of the installed base.",
    "tax_rate": "Statutory rate; NOLs ignored for simplicity.",
    "nwc_pct_revenue_change": "Customer prepayments partly offset receivables.",
    "debt_funded_share_of_capex": "Historical financing mix of asset-backed and unsecured debt.",
    "new_debt_rate": "Recent issuance levels for comparable high-yield infrastructure credits.",
    "wacc": "High-beta, highly levered equity; cost of capital set conservatively.",
    "terminal_growth": "Long-run nominal growth after the build-out phase.",
    "mw_additions_per_year": "Pace of new contracted capacity.",
    "energization_rate": "Share of the contracted-but-dark backlog brought online each year.",
    "utilization": "Share of GPU-hours sold across the fleet.",
    "price_per_gpu_hour_new": "Blended price per GPU-hour for newest generation.",
    "price_new_growth_per_year": "Newest-generation pricing assumed flat in nominal terms.",
    "price_decay_per_year_of_age": "Discount per year of hardware age as new generations arrive.",
}


def A(driver, value, rationale=None, epistemic="analyst_assumption", basis=()):
    return {"driver": driver, "value": value, "epistemic": epistemic, "basis_claims": list(basis),
            "rationale": rationale or GENERIC[driver]}


def base(overrides: dict, special: dict):
    out = []
    for k, v in {**REF, **overrides}.items():
        out.append(special.get(k) or A(k, v))
    return out


def C(id, text, epi, cites, metric=None, value=None, unit=None, period=None):
    return {"id": id, "text": text, "epistemic": epi, "citations": cites, "metric": metric, "value": value,
            "unit": unit, "period": period}


def T(desc, metric, op, thr, unit=""):
    return {"description": desc, "metric": metric, "operator": op, "threshold": thr, "unit": unit}


reports = {}

reports["value"] = {
    "thesis": "Reported earnings overstate the economics: maintenance capex on a six-year accounting life with a shorter "
              "economic life leaves little free cash flow for equity after debt service. No margin of safety at $45.",
    "stance": "negative",
    "key_points": ["Debt of $20bn plus $15bn of leases sits ahead of equity.",
                   "Depreciation life was extended from four to six years in 2024.",
                   "Management's >90% utilization figure is a company statement, not an audited fact."],
    "claims": [
        C("c1", "Total debt was $20.0bn at June 30, 2026.", "verified_fact", ["EV-001"], "total_debt", 20.0, "USD_bn", "2026-06-30"),
        C("c2", "Fleet utilization is 92%.", "verified_fact", ["EV-003"], "fleet_utilization", 0.92, "fraction", "2026-09"),
        C("c3", "GPU servers are depreciated over six years.", "verified_fact", ["EV-009"], "gpu_depreciation_life", 6, "years", "FY2025"),
        C("c4", "If economic life is shorter than the accounting life, reported EBIT overstates sustainable earnings.",
          "analyst_assumption", []),
    ],
    "scenarios": [
        {"name": "base", "probability": 0.5, "assumptions": base(
            dict(utilization=0.83, price_per_gpu_hour_new=2.95, price_decay_per_year_of_age=0.13, wacc=0.11,
                 terminal_growth=0.02, mw_additions_per_year=400),
            {"utilization": A("utilization", 0.83, "Haircut to management's >90% claim, which is unaudited.", basis=["c2"]),
             "wacc": A("wacc", 0.11, "Levered equity with refinancing needs warrants a higher discount rate.")})},
        {"name": "bear", "probability": 0.3, "assumptions": [
            A("utilization", 0.72, "Overbuild in 2027-28 pushes utilization down."),
            A("price_per_gpu_hour_new", 2.6, "Contract repricing toward on-demand levels."),
            A("price_decay_per_year_of_age", 0.18, "Faster obsolescence as new generations ship annually.")]},
        {"name": "bull", "probability": 0.2, "assumptions": [
            A("utilization", 0.88, "Long-term contracts keep the fleet full."),
            A("price_per_gpu_hour_new", 3.2, "Scarcity pricing persists for newest generation.")]},
    ],
    "uncertainties": ["Economic life of current-generation GPUs is unobserved.",
                      "Customer contract terms (take-or-pay vs cancellable) are not disclosed in the dossier."],
    "invalidation_triggers": [T("Audited utilization stays above 90% through 2027", "fleet_utilization", ">", 0.90, "fraction")],
}

reports["growth"] = {
    "thesis": "Contracted power of 2.5 GW against 0.9 GW energised is a multi-year revenue runway; at management's "
              "$3.00 contracted pricing the build-out compounds equity value.",
    "stance": "positive",
    "key_points": ["1.6 GW of contracted-but-dark capacity.", "Management targets 400-600 MW of additions per year.",
                   "Newest-generation capacity contracted around $3.00 per GPU-hour."],
    "claims": [
        C("c1", "Management targets 400-600 MW of new contracted power per year.", "management_guidance", ["EV-003"],
          "mw_additions_per_year", 500, "MW", "2027-2030"),
        C("c2", "Active power reached 950 MW at quarter end.", "verified_fact", ["EV-002"], "active_power_mw", 950, "MW", "2026-06-30"),
        C("c3", "Remaining performance obligations were $75bn.", "verified_fact", ["EV-001"],
          "remaining_performance_obligations", 75.0, "USD_bn", "2026-06-30"),
        C("c4", "New-generation clusters are contracted at about $3.00 per GPU-hour.", "management_guidance", ["EV-003"],
          "contracted_price_per_gpu_hour_new", 3.0, "USD_per_hour", "2026-09"),
    ],
    "scenarios": [
        {"name": "base", "probability": 0.5, "assumptions": base(
            dict(utilization=0.88, price_per_gpu_hour_new=3.0, price_decay_per_year_of_age=0.11, mw_additions_per_year=550,
                 energization_rate=0.40, terminal_growth=0.03),
            {"mw_additions_per_year": A("mw_additions_per_year", 550, "Upper half of management's range given demand.",
                                        "management_guidance", ["c1"]),
             "price_per_gpu_hour_new": A("price_per_gpu_hour_new", 3.0, "Management's contracted price.",
                                         "management_guidance", ["c4"]),
             "energization_rate": A("energization_rate", 0.40, "Power is contracted; energisation is an execution question.")})},
        {"name": "bear", "probability": 0.2, "assumptions": [
            A("utilization", 0.80, "Temporary digestion period."),
            A("energization_rate", 0.30, "Grid equipment delays.")]},
        {"name": "bull", "probability": 0.3, "assumptions": [
            A("energization_rate", 0.55, "A $75bn backlog forces rapid energisation.", basis=["c3"]),
            A("utilization", 0.92, "Management's current utilization holds.")]},
    ],
    "uncertainties": ["Customer concentration not addressed in this report."],
    "invalidation_triggers": [T("New contracted MW falls below 300 MW in a year", "mw_additions_per_year", "<", 300, "MW")],
}

reports["credit"] = {
    "thesis": "The enterprise can grow, but equity holders capture little of it: refinancing $9bn of maturities over three "
              "years at higher rates and funding 30% of capex internally leaves coverage adequate but thin.",
    "stance": "neutral",
    "key_points": ["Weighted average rate 9.0%; recent notes priced at 9.25%.",
                   "$9bn matures within 36 months.", "$15bn of lease liabilities is effectively debt-like."],
    "claims": [
        C("c1", "Weighted average interest rate on debt was 9.0%.", "verified_fact", ["EV-001"], "weighted_avg_interest_rate", 9.0, "pct", "2026-06-30"),
        C("c2", "Recent senior notes priced at a 9.25% coupon.", "verified_fact", ["EV-008"], "new_notes_coupon", 9.25, "pct", "2026-09"),
        C("c3", "$4.0bn of debt matures in months 13-24.", "verified_fact", ["EV-001"], "debt_maturities_y2", 4.0, "USD_bn", "2026-06-30"),
        C("c4", "Lease liabilities were $15.0bn.", "verified_fact", ["EV-001"], "lease_liabilities", 15.0, "USD_bn", "2026-06-30"),
    ],
    "scenarios": [
        {"name": "base", "probability": 0.5, "assumptions": base(
            dict(wacc=0.115, new_debt_rate=0.095, terminal_growth=0.02),
            {"new_debt_rate": A("new_debt_rate", 0.095, "Recent 9.25% notes plus a modest premium for refinancing size.", basis=["c2"]),
             "wacc": A("wacc", 0.115, "Credit spreads imply equity risk premium above market.")})},
        {"name": "bear", "probability": 0.3, "assumptions": [
            A("wacc", 0.13, "Spread widening in a credit downturn."),
            A("new_debt_rate", 0.11, "Refinancing at distressed levels."),
            A("utilization", 0.78, "Weaker demand in a downturn.")]},
        {"name": "bull", "probability": 0.2, "assumptions": [A("wacc", 0.105, "Investment-grade trajectory.")]},
    ],
    "uncertainties": ["Covenant terms are not in the dossier.", "Maturities beyond 36 months are not disclosed in the dossier."],
    "invalidation_triggers": [T("Interest coverage falls below 2.5x", "interest_coverage", "<", 2.5, "x")],
}

reports["industry"] = {
    "thesis": "Prior-generation pricing has fallen roughly 30% in a year and the largest customer is building its own "
              "capacity; installed-fleet revenue productivity will decay faster than management implies.",
    "stance": "negative",
    "key_points": ["H100-class pricing at $2.20, down ~30% y/y.", "Survey shows 15-20% price decline per year of age.",
                   "Largest customer plans self-built capacity."],
    "claims": [
        C("c1", "Median prior-generation pricing is $2.20 per GPU-hour.", "third_party_estimate", ["EV-005"],
          "gpu_hour_price_prior_gen", 2.2, "USD_per_hour", "2026-09"),
        C("c2", "Prices decline about 17.5% per year of hardware age.", "third_party_estimate", ["EV-005"],
          "price_decay_per_year_of_age", 0.175, "fraction", "2026"),
        C("c3", "The largest customer plans to bring 1 GW of self-built capacity online by 2028.", "third_party_estimate",
          ["EV-006", "EV-007"]),
    ],
    "scenarios": [
        {"name": "base", "probability": 0.5, "assumptions": base(
            dict(utilization=0.84, price_per_gpu_hour_new=2.95, price_decay_per_year_of_age=0.16),
            {"price_decay_per_year_of_age": A("price_decay_per_year_of_age", 0.16,
                                              "Slightly below the survey's 17.5% because part of the fleet is on fixed-price contracts.",
                                              basis=["c2"])})},
        {"name": "bear", "probability": 0.3, "assumptions": [
            A("gpu_economic_life_years", 5, "Annual GPU launches shorten useful service life."),
            A("price_decay_per_year_of_age", 0.20, "Top of the survey range.")]},
        {"name": "bull", "probability": 0.2, "assumptions": [
            A("price_decay_per_year_of_age", 0.12, "Supply constraints keep older hardware in demand.")]},
    ],
    "uncertainties": ["Share of fleet on fixed-price multi-year contracts is unknown."],
    "invalidation_triggers": [T("Prior-generation pricing stabilises above $2.50", "gpu_hour_price_prior_gen", ">", 2.5, "USD_per_hour")],
}

reports["contrarian"] = {
    "thesis": "The market treats the 2.5 GW contracted figure as revenue in waiting. Only 40% of RPO converts within 24 "
              "months and one customer is 60% of revenue; the real constraint is energisation pace, not demand.",
    "stance": "negative",
    "key_points": ["60% revenue concentration in one customer.", "40% of RPO recognised within 24 months.",
                   "2024 depreciation-life change flattered earnings by $1.1bn.",
                   "A blog claim of 100% industry utilization is unsupported and flagged."],
    "claims": [
        C("c1", "One customer accounted for 60% of quarterly revenue.", "verified_fact", ["EV-001"],
          "largest_customer_revenue_share", 60, "pct", "Q2-2026"),
        C("c2", "The 2024 useful-life extension reduced depreciation by $1.1bn.", "verified_fact", ["EV-009"],
          "depreciation_life_change_benefit", 1.1, "USD_bn", "FY2024"),
        C("c3", "About 40% of RPO is expected to be recognised within 24 months.", "verified_fact", ["EV-001"],
          "rpo_recognized_24m_share", 40, "pct", "2026-06-30"),
        C("c4", "Some commentary claims industry utilization is at 100%.", "speculation", ["EV-010"]),
    ],
    "scenarios": [
        {"name": "base", "probability": 0.45, "assumptions": base(
            dict(utilization=0.80, price_decay_per_year_of_age=0.13, energization_rate=0.28),
            {"energization_rate": A("energization_rate", 0.28,
                                    "Slow RPO conversion (40% in 24 months) implies energisation well below backlog pace.",
                                    basis=["c3"])})},
        {"name": "bear", "probability": 0.35, "assumptions": [
            A("energization_rate", 0.20, "Transformer lead times extend further."),
            A("utilization", 0.70, "Largest customer shifts load in-house.")]},
        {"name": "bull", "probability": 0.2, "assumptions": [A("utilization", 0.86, "Customer diversification succeeds.")]},
    ],
    "uncertainties": ["Whether the largest customer's contracts are take-or-pay."],
    "invalidation_triggers": [T("Largest customer share falls below 40% of revenue", "largest_customer_revenue_share", "<", 0.40, "fraction")],
}

# ---------------- stage 3: cross-examination ----------------
challenge = {
    "industry": {"challenges": [
        {"target_role": "growth", "driver": "price_decay_per_year_of_age",
         "question": "The September survey shows prior-generation prices falling 15-20% per year of age and H100-class pricing "
                     "down ~30% y/y. What evidence supports your 11%?",
         "counter_value": 0.175, "evidence_ids": ["EV-005"]}]},
    "growth": {"challenges": [
        {"target_role": "industry", "driver": "price_decay_per_year_of_age",
         "question": "Most of the fleet is on multi-year contracts at about $3.00. Does a spot-market survey describe "
                     "contracted revenue at all?", "evidence_ids": ["EV-003"]},
        {"target_role": "contrarian", "driver": "utilization",
         "question": "Management reports fleet utilization above 90%. What evidence supports 80%?",
         "counter_value": 0.90, "evidence_ids": ["EV-003"]},
        {"target_role": "credit", "driver": "wacc",
         "question": "Isn't 11.5% too punitive for a business with $55bn of contracted backlog?"},
        {"target_role": "value", "driver": "utilization", "question": "Unassigned challenge - should be dropped."}]},
    "contrarian": {"challenges": [
        {"target_role": "growth", "driver": "utilization",
         "question": "60% of revenue comes from one customer that is building 1 GW of its own capacity. Why is 88% "
                     "utilization durable through 2028?", "counter_value": 0.80, "evidence_ids": ["EV-001", "EV-006"]}]},
    "credit": {"challenges": [
        {"target_role": "growth", "driver": "wacc",
         "question": "New unsecured notes priced at 9.25% with a 4.3% 10-year Treasury. How is 10.5% a cost of capital "
                     "for the equity-heavy marginal dollar?", "evidence_ids": ["EV-008", "EV-014"]}]},
}
respond = {
    "growth": {"responses": [
        {"challenge_id": "industry->growth:price_decay_per_year_of_age", "concedes": True,
         "response": "I had not seen the pricing survey. Contracted pricing softens the effect but 11% is too low; I will move "
                     "toward the survey range.", "evidence_ids": ["EV-005"]},
        {"challenge_id": "contrarian->growth:utilization", "concedes": False,
         "response": "Concentration is real, but the self-build is a 2028 event and current contracts run multiple years. "
                     "I keep 88% for the base case and lower the bear case.", "evidence_ids": ["EV-003"]},
        {"challenge_id": "credit->growth:wacc", "concedes": False,
         "response": "The 9.25% coupon is a debt cost; with ~50% debt weighting 10.5% is defensible.", "evidence_ids": ["EV-008"]}]},
    "industry": {"responses": [
        {"challenge_id": "growth->industry:price_decay_per_year_of_age", "concedes": False,
         "response": "Contract terms are not disclosed in the dossier, so the share of the fleet protected from spot pricing "
                     "is unknown. Survey-based decay remains the best available evidence.", "evidence_ids": ["EV-005"]}]},
    "contrarian": {"responses": [
        {"challenge_id": "growth->contrarian:utilization", "concedes": True,
         "response": "Management's >90% is unaudited guidance, but it is evidence I had ignored. I move partway.",
         "evidence_ids": ["EV-003"]}]},
    "credit": {"responses": [
        {"challenge_id": "growth->credit:wacc", "concedes": False,
         "response": "Backlog does not lower the cost of capital if it is concentrated in one counterparty."}]},
}
revise = {
    "growth": {
        "changes": [
            {"scenario": "base", "driver": "price_decay_per_year_of_age", "new_value": 0.15,
             "reason": "Pricing survey shows 15-20% decline per year of age; contracted pricing justifies the low end.",
             "basis_challenge_ids": ["industry->growth:price_decay_per_year_of_age"], "basis_evidence_ids": ["EV-005"]},
            {"scenario": "bull", "driver": "energization_rate", "new_value": 0.50,
             "reason": "Restated without the backlog figure: management cites 6-12 month delivery lags, so half the dark "
                       "backlog per year is achievable in a strong case.", "basis_evidence_ids": ["EV-003"]},
            {"scenario": "bear", "driver": "utilization", "new_value": 0.75,
             "reason": "Contrarian's concentration point justifies a lower bear case.",
             "basis_challenge_ids": ["contrarian->growth:utilization"], "basis_evidence_ids": ["EV-001"]}],
        "retained_view_reason": "Base utilization and WACC retained: arguments did not change the evidence on current contracts.",
        "new_claims": [{"id": "r1", "text": "Active power was 900 MW at quarter end (corrected release).", "epistemic": "verified_fact",
                        "citations": ["EV-013"], "metric": "active_power_mw", "value": 900, "unit": "MW", "period": "2026-06-30"}]},
    "industry": {"changes": [], "retained_view_reason": "Growth's challenge relies on undisclosed contract terms; the survey "
                 "remains the best evidence."},
    "contrarian": {"changes": [
        {"scenario": "base", "driver": "utilization", "new_value": 0.83,
         "reason": "Management's unaudited >90% claim is weak evidence but not zero; moving partway.",
         "basis_challenge_ids": ["growth->contrarian:utilization"], "basis_evidence_ids": ["EV-003"]}]},
    "credit": {"changes": [
        {"scenario": "base", "driver": "wacc", "new_value": 0.108,
         "reason": "On reflection the growth analyst's point about backlog has some merit.",
         "basis_challenge_ids": ["growth->credit:wacc"]}]},
    "value": {"changes": [
        {"scenario": "base", "driver": "utilization", "new_value": 0.86,
         "reason": "The debate suggests demand is stronger than I assumed."}]},
}
risk = {"narrative": "SCRIPTED FIXTURE. Coverage and leverage limits pass in the median-assumption case, but the pooled "
                     "distribution places substantial weight on equity being impaired: the equity is a levered call on "
                     "utilization and pricing. Cohort economics are positive but thin relative to the cost of capital.",
        "additional_risks": ["Single-customer concentration (60% of revenue) is not modelled as a discrete event.",
                             "Contract cancellability is unknown; take-or-pay terms would change the bear case materially.",
                             "Maturities beyond 36 months are not in the dossier, so refinancing risk is understated."]}
chair = {"primary_thesis": "SCRIPTED FIXTURE. Value depends on GPU-hour pricing holding up as the fleet ages; the pricing "
                           "survey (EV-005) and the 2024 useful-life extension (EV-009) suggest reported earnings overstate "
                           "sustainable cash generation.",
         "strongest_opposing_thesis": "Contracted power of 2.5 GW against 0.9 GW energised (EV-013) and management's $3.00 "
                                      "contracted pricing (EV-003) could support rapid growth if energisation accelerates.",
         "catalysts": ["Q3 energised MW versus the 1.6 GW dark backlog", "Repricing of the next large contract renewal",
                       "Refinancing of the $4.0bn year-2 maturity (EV-001)"],
         "key_risks": ["The majority of analysts agree pricing decay is underappreciated.",
                       "60% customer concentration (EV-001)."],
         "unresolved_questions": ["What share of revenue is on take-or-pay contracts?", "Economic life of current GPUs?"],
         "reconsideration_triggers": [
             {"description": "Energised MW exceeds 1,400 by mid-2027", "metric": "active_power_mw", "operator": ">", "threshold": 1400, "unit": "MW"},
             {"description": "Prior-generation pricing stabilises above $2.50", "metric": "gpu_hour_price_prior_gen", "operator": ">", "threshold": 2.5, "unit": "USD_per_hour"}],
         "cited_evidence": ["EV-005", "EV-009", "EV-013", "EV-003", "EV-001"]}

if __name__ == "__main__":
    for stage, d in (("challenge", challenge), ("respond", respond), ("revise", revise)):
        for role, body in d.items():
            (OUT / f"{role}.{stage}.json").write_text(json.dumps(body, indent=1))
    (OUT / "risk_manager.risk.json").write_text(json.dumps(risk, indent=1))
    (OUT / "chair.chair.json").write_text(json.dumps(chair, indent=1))
    OUT.mkdir(parents=True, exist_ok=True)
    for role, r in reports.items():
        (OUT / f"{role}.stage1.json").write_text(json.dumps(r, indent=1))
    print("wrote", sorted(reports))
