from datetime import date

from icommittee.ingest.sec import extract


def row(v, end, accn, form, filed, start=None):
    r = {"val": v, "end": end, "accn": accn, "form": form, "filed": filed}
    if start:
        r["start"] = start
    return r


def payload():
    q2 = ("0001-26-000002", "10-Q", "2026-08-10")
    q2a = ("0001-26-000003", "10-Q/A", "2026-09-01")
    return {"facts": {"us-gaap": {
        "LongTermDebtCurrent": {"units": {"USD": [row(1e9, "2026-06-30", *q2), row(1e9, "2025-12-31", *q2)]}},
        "LongTermDebtNoncurrent": {"units": {"USD": [row(15e9, "2026-06-30", *q2), row(12e9, "2025-12-31", *q2),
                                                     row(16e9, "2026-06-30", *q2a)]}},
        "CashAndCashEquivalentsAtCarryingValue": {"units": {"USD": [row(2e9, "2026-06-30", *q2)]}},
        "Revenues": {"units": {"USD": [row(3.4e9, "2026-06-30", *q2, start="2026-04-01"),
                                       row(6.1e9, "2026-06-30", *q2, start="2026-01-01")]}},
    }, "dei": {"EntityCommonStockSharesOutstanding": {"units": {"shares": [row(4.8e8, "2026-08-01", *q2)]}}}}}


def test_debt_is_total_not_current_portion():
    evs = extract(payload(), "Demo")
    q2 = next(e for e in evs if e.id.endswith("000002"))
    debt = next(d for d in q2.datapoints if d.metric == "total_debt")
    assert debt.value == 16e9 and debt.period == "2026-06-30"


def test_comparatives_dropped_and_dates_honest():
    q2 = next(e for e in extract(payload(), "Demo") if e.id.endswith("000002"))
    assert all(d.period.endswith("2026-06-30") or d.metric == "basic_shares_outstanding" for d in q2.datapoints)
    assert q2.as_of == date(2026, 6, 30) and q2.published == date(2026, 8, 10)


def test_revenue_uses_filings_own_quarter():
    q2 = next(e for e in extract(payload(), "Demo") if e.id.endswith("000002"))
    rev = next(d for d in q2.datapoints if d.metric == "revenue")
    assert rev.value == 3.4e9 and rev.period == "2026-04-01..2026-06-30"


def test_amendment_supersedes_original():
    evs = {e.id: e for e in extract(payload(), "Demo")}
    amended = evs["SEC-0001-26-000003"]
    assert amended.supersedes == "SEC-0001-26-000002"
    # The amendment restates only the noncurrent piece, so total debt can't be rebuilt from it.
    # It must go missing (human reconciles) rather than leave the stale original total in force.
    assert not any(d.metric == "total_debt" for d in amended.datapoints)
    from icommittee.evidence.registry import EvidenceRegistry
    reg = EvidenceRegistry(date(2026, 10, 9))
    reg.extend(evs.values())
    assert reg.status("SEC-0001-26-000002") == "superseded" and reg.best_fact("total_debt") is None
