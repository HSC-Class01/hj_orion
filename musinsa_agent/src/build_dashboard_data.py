from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DASH_DATA = ROOT / "dashboard" / "data"
DASH_DATA.mkdir(parents=True, exist_ok=True)


def pct(a, b):
    if pd.isna(a) or pd.isna(b) or b in (0, None):
        return None
    return float(a / b * 100)


def make_ratios(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(["period", "year"]).copy()
    out = []
    for period, g in df.groupby("period", sort=False):
        g = g.sort_values("year").copy()
        g["revenue_growth"] = g["revenue"].pct_change() * 100
        g["operating_margin"] = g.apply(lambda r: pct(r["operating_income"], r["revenue"]), axis=1)
        g["net_margin"] = g.apply(lambda r: pct(r["net_income"], r["revenue"]), axis=1)
        g["ocf_margin"] = g.apply(lambda r: pct(r["operating_cash_flow"], r["revenue"]), axis=1)
        g["debt_ratio"] = g.apply(lambda r: pct(r["total_liabilities"], r["total_equity"]), axis=1)
        g["equity_ratio"] = g.apply(lambda r: pct(r["total_equity"], r["total_assets"]), axis=1)
        g["roa"] = g.apply(lambda r: pct(r["net_income"], r["total_assets"]), axis=1)
        g["roe"] = g.apply(lambda r: pct(r["net_income"], r["total_equity"]), axis=1)
        out.append(g)
    return pd.concat(out, ignore_index=True) if out else df


def clean_records(df: pd.DataFrame):
    return json.loads(df.where(pd.notna(df), None).to_json(orient="records", force_ascii=False))


def main():
    f = pd.read_csv(DATA / "financials.csv")
    for col in f.columns:
        if col not in {"period", "fs_div", "corp_code", "corp_name", "rcept_no", "filing_url", "reprt_code"}:
            f[col] = pd.to_numeric(f[col], errors="coerce")
    ratios = make_ratios(f)
    ratios.to_csv(DATA / "ratios.csv", index=False, encoding="utf-8-sig")

    filings = pd.read_csv(DATA / "filings.csv") if (DATA / "filings.csv").exists() else pd.DataFrame()
    company = json.loads((DATA / "company.json").read_text(encoding="utf-8")) if (DATA / "company.json").exists() else {}
    settings = json.loads((ROOT / "config" / "settings.json").read_text(encoding="utf-8"))

    (DASH_DATA / "financials.json").write_text(json.dumps(clean_records(f), ensure_ascii=False), encoding="utf-8")
    (DASH_DATA / "ratios.json").write_text(json.dumps(clean_records(ratios), ensure_ascii=False), encoding="utf-8")
    (DASH_DATA / "filings.json").write_text(json.dumps(clean_records(filings), ensure_ascii=False), encoding="utf-8")
    metadata = {
        "company": company,
        "updated_at": pd.Timestamp.now(tz="Asia/Seoul").isoformat(),
        "start_year_requested": settings["start_year"],
        "structured_api_start_year": settings["dart_financial_data_start_year"],
        "report_codes": settings["report_codes"],
        "peerfirms": settings["peerfirms"],
    }
    (DASH_DATA / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Dashboard data built: {len(f)} periods")


if __name__ == "__main__":
    main()
