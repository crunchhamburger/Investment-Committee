"""Role definitions.

Roles differ in *objective* (what they are paid to find), *required
questions* (forced coverage), and *evidence view* (which secondary sources
they see). All roles see the same primary facts. Personality is
deliberately absent: it adds tokens, not information.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RoleSpec:
    name: str
    title: str
    objective: str
    must_answer: tuple[str, ...]
    evidence_topics: tuple[str, ...] = field(default_factory=tuple)  # secondary-evidence view; () = all


ROLES: dict[str, RoleSpec] = {r.name: r for r in [
    RoleSpec(
        "value", "Value Analyst",
        "Intrinsic value, downside protection, capital allocation, free cash flow and margin of safety.",
        ("Which operating assumptions would justify a high valuation, and which of them look excessive?",
         "What is free cash flow after maintenance capex at the end of the horizon?",
         "Where is the margin of safety, if any?"),
        ("valuation", "capital_allocation", "accounting")),
    RoleSpec(
        "growth", "Growth Analyst",
        "Addressable market, revenue growth, competitive advantage, customer economics and reinvestment.",
        ("Which growth is durable and which reflects temporary industry conditions?",
         "What are the unit economics of incremental capacity?",
         "How fast can contracted capacity actually be energised and sold?"),
        ("demand", "market", "customers")),
    RoleSpec(
        "credit", "Credit and Capital Structure Analyst",
        "Debt, liquidity, coverage, refinancing, covenants, dilution and who captures value: "
        "creditors, customers or shareholders.",
        ("Does enterprise growth translate into equity value after financing costs?",
         "What happens at the next maturities if refinancing costs rise?",
         "How much external equity does the plan need?"),
        ("financing", "debt", "rates")),
    RoleSpec(
        "industry", "Industry and Competitive Dynamics Analyst",
        "Industry structure, entry barriers, competitors, supply chain, pricing power, technology shifts.",
        ("How could competitors or customers invalidate the company's pricing and utilisation?",
         "What do new GPU generations do to the revenue productivity of the installed fleet?",
         "Who holds bargaining power in the supply chain?"),
        ("competition", "supply_chain", "pricing", "technology")),
    RoleSpec(
        "contrarian", "Contrarian Analyst",
        "Falsification. Build the strongest credible case against the prevailing thesis, whatever its "
        "direction. Do not default to bearish: if the market is too pessimistic, say so.",
        ("What is the market implicitly assuming, and what evidence contradicts it?",
         "Which accounting choices flatter reported results?",
         "What single observation would most cleanly falsify the leading thesis?"),
        ()),
]}

RISK_MANAGER = RoleSpec(
    "risk_manager", "Risk Manager",
    "Independent downside review: drawdown, leverage, liquidity, concentration, model uncertainty, "
    "probability of permanent impairment. Binding vetoes come only from the written risk policy.",
    ("Which rule-based limits bind?", "What risks are not captured by the model at all?"))

CHAIR = RoleSpec(
    "chair", "Investment Committee Chair",
    "Synthesise evidence and disagreements without forcing consensus. Agreement among AI analysts is "
    "not evidence. Preserve dissent.",
    ("What is the primary thesis and its evidence?", "What is the strongest opposing thesis?",
     "What specific observations would change the decision?"))
