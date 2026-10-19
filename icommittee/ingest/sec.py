"""SEC XBRL companyfacts -> draft dossier.

Fixes over the MVP extractor:
  * Total debt is LongTermDebt (which includes the current portion) or the SUM of
    current + noncurrent components from the SAME filing and SAME period end. A
    lone current-portion figure is never reported as total debt.
  * One Evidence record per filing (accession), dated by its filing date, with
    as_of = period end. Nothing is stamped with today's date.
  * Only each filing's own reporting period is kept; prior-period comparatives
    are dropped so they don't masquerade as current figures.
  * Amendments (10-Q/A, 10-K/A) supersede the original filing for the same period.
  * Operational metrics XBRL doesn't carry (MW, debt maturities by year, option
    strikes) are left missing for a human to add from primary documents.

Requires SEC_USER_AGENT="Name email@domain" per SEC fair-access policy.
"""
from __future__ import annotations

import json
import os
import urllib.request
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from ..schemas import DataPoint, Epistemic, Evidence, SourceKind, SourceTier

TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

# metric -> list of strategies; each strategy is a list of concepts that must ALL be present and are summed.
INSTANT = {
    "total_debt": [["LongTermDebt"], ["LongTermDebtCurrent", "LongTermDebtNoncurrent"],
                   ["DebtCurrent", "LongTermDebtNoncurrent"]],
    "cash_and_equivalents": [["CashAndCashEquivalentsAtCarryingValue"]],
    "lease_liabilities": [["OperatingLeaseLiability", "FinanceLeaseLiability"], ["OperatingLeaseLiability"]],
    "ppe_net": [["PropertyPlantAndEquipmentNet"]],
    "preferred_equity": [["PreferredStockValue"]],
    "noncontrolling_interest": [["MinorityInterest"]],
}
SHARES = [("dei", "EntityCommonStockSharesOutstanding"), ("us-gaap", "CommonStockSharesOutstanding")]
DURATION = {"revenue": [["RevenueFromContractWithCustomerExcludingAssessedTax"], ["Revenues"]]}


def _fetch(url: str, ua: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept-Encoding": "identity"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def extract(facts: dict, company: str, max_filings: int = 6, now: Optional[datetime] = None) -> list[Evidence]:
    now = now or datetime.now(timezone.utc)
    gaap = facts.get("facts", {}).get("us-gaap", {})
    dei = facts.get("facts", {}).get("dei", {})
    by_accn: dict[str, dict] = defaultdict(lambda: {"rows": defaultdict(dict), "form": None, "filed": None,
                                                    "end": None, "fy": None, "fp": None})

    for ns, src in (("us-gaap", gaap), ("dei", dei)):
        for concept, body in src.items():
            for unit, items in body.get("units", {}).items():
                for it in items:
                    if it.get("form", "").split("/")[0] not in ("10-K", "10-Q") or it.get("val") is None:
                        continue
                    a = by_accn[it["accn"]]
                    a["form"], a["filed"] = it["form"], it["filed"]
                    key = (ns, concept, unit, it.get("start"), it["end"])
                    a["rows"][key] = it["val"]
                    if ns == "us-gaap" and "start" not in it:
                        a["end"] = max(a["end"] or it["end"], it["end"])

    accns = sorted((k for k, v in by_accn.items() if v["end"]), key=lambda k: by_accn[k]["filed"], reverse=True)
    accns = accns[:max_filings]
    out: list[Evidence] = []
    originals: dict[tuple[str, str], str] = {}
    for accn in sorted(accns, key=lambda k: by_accn[k]["filed"]):
        a = by_accn[accn]
        end = a["end"]
        dps, notes = [], []
        for metric, strategies in INSTANT.items():
            for strat in strategies:
                vals = [a["rows"].get(("us-gaap", c, "USD", None, end)) for c in strat]
                if all(v is not None for v in vals):
                    dps.append(DataPoint(metric=metric, value=float(sum(vals)), unit="USD", period=end,
                                         basis=Epistemic.VERIFIED_FACT))
                    notes.append(f"{metric}={' + '.join(strat)}")
                    break
        for ns, concept in SHARES:
            cands = [(k[4], v) for k, v in a["rows"].items() if k[0] == ns and k[1] == concept and k[2] == "shares"]
            if cands:
                d_end, v = max(cands)
                dps.append(DataPoint(metric="basic_shares_outstanding", value=float(v), unit="shares",
                                     period=d_end, basis=Epistemic.VERIFIED_FACT))
                notes.append(f"shares={ns}:{concept} as of {d_end}")
                break
        for metric, strategies in DURATION.items():
            for strat in strategies:
                hits = [(k[3], v) for k, v in a["rows"].items()
                        if k[1] == strat[0] and k[2] == "USD" and k[4] == end and k[3]]
                if hits:
                    start, v = max(hits)  # latest start = the filing's own (shortest) period
                    dps.append(DataPoint(metric=metric, value=float(v), unit="USD", period=f"{start}..{end}",
                                         basis=Epistemic.VERIFIED_FACT))
                    break
        amendment = a["form"].endswith("/A")
        if not dps and not amendment:
            continue
        if amendment:
            changed = sorted({k[1] for k in a["rows"] if k[4] == end})
            notes.append("AMENDMENT restating " + ", ".join(changed)
                         + "; totals not recomputable from this filing alone are deliberately absent")
        eid = f"SEC-{accn}"
        supersedes = None
        if a["form"].endswith("/A") and (a["form"][:-2], end) in originals:
            supersedes = originals[(a["form"][:-2], end)]
        else:
            originals[(a["form"], end)] = eid
        out.append(Evidence(
            id=eid, title=f"{company} {a['form']} for period ended {end}", publisher="SEC EDGAR XBRL companyfacts",
            url=f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&accession={accn}",
            tier=SourceTier.PRIMARY, kind=SourceKind.SEC_FILING, published=date.fromisoformat(a["filed"]),
            retrieved_at=now, as_of=date.fromisoformat(end),
            excerpt=("XBRL facts extracted for the filing's own reporting period. Concepts: " + "; ".join(notes)
                     + ". Verify against the filing text; XBRL tagging can differ across issuers."),
            datapoints=dps, topics=["financing", "debt", "accounting"], root_source=f"sec:{accn}",
            supersedes=supersedes))
    return out


def build_dossier(ticker: str, out: Path, session_date: Optional[str] = None,
                  fetch: Callable[[str, str], dict] = _fetch) -> dict:
    ua = os.getenv("SEC_USER_AGENT", "")
    if "@" not in ua:
        raise SystemExit('Set SEC_USER_AGENT="Your Name you@example.com" (SEC fair-access requirement).')
    tickers = fetch(TICKERS_URL, ua)
    match = next((t for t in tickers.values() if t["ticker"].upper() == ticker.upper()), None)
    if not match:
        raise SystemExit(f"{ticker} not found in SEC ticker list")
    facts = fetch(FACTS_URL.format(cik=str(match["cik_str"]).zfill(10)), ua)
    evs = extract(facts, match["title"])
    dossier = {"company": f"{match['title']} ({ticker.upper()})",
               "session_date": session_date or date.today().isoformat(),
               "evidence": [json.loads(e.model_dump_json()) for e in evs]}
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(dossier, indent=1))
    return dossier
