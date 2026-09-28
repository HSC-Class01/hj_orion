from __future__ import annotations

import io
import json
import os
import re
import zipfile
from pathlib import Path
from typing import Any

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "config" / "settings.json").read_text(encoding="utf-8"))
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
DATA_DIR.mkdir(exist_ok=True)
RAW_DIR.mkdir(exist_ok=True)

API_KEY = os.getenv("DART_API_KEY", "").strip()
BASE = "https://opendart.fss.or.kr/api"
TIMEOUT = 60

REPORT_CODES = CONFIG["report_codes"]
PERIODS = [
    ("annual", REPORT_CODES["annual"]),
    ("half_year", REPORT_CODES["half_year"]),
    ("quarterly", REPORT_CODES["quarterly_q1"]),
    ("quarterly", REPORT_CODES["quarterly_q3"]),
]

ALIASES = {
    "revenue": ["매출액", "영업수익", "수익(매출액)", "매출", "영업수익(매출액)"],
    "operating_income": ["영업이익", "영업이익(손실)"],
    "net_income": ["당기순이익", "당기순이익(손실)", "분기순이익", "반기순이익"],
    "operating_cash_flow": ["영업활동현금흐름", "영업활동으로 인한 현금흐름"],
    "total_assets": ["자산총계"],
    "total_liabilities": ["부채총계"],
    "total_equity": ["자본총계"],
    "cash": ["현금및현금성자산", "현금및현금성자산(현금성자산 포함)", "현금 및 현금성자산"],
    "inventory": ["재고자산", "재고자산(상품 및 제품)"]
}


def require_key() -> None:
    if not API_KEY:
        raise RuntimeError("DART_API_KEY 환경변수가 없습니다. GitHub Actions Secret 또는 로컬 환경변수로 설정하세요.")


def get_json(url: str, params: dict[str, Any]) -> dict[str, Any]:
    r = requests.get(url, params=params, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    if str(data.get("status")) != "000":
        raise RuntimeError(f"OpenDART API error {data.get('status')}: {data.get('message')}")
    return data


def download_corp_code() -> pd.DataFrame:
    require_key()
    r = requests.get(f"{BASE}/corpCode.xml", params={"crtfc_key": API_KEY}, timeout=TIMEOUT)
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        xml_name = next(n for n in zf.namelist() if n.lower().endswith("corpcode.xml"))
        xml = zf.read(xml_name)
    import xml.etree.ElementTree as ET
    root = ET.fromstring(xml)
    rows = []
    for item in root.findall("list"):
        rows.append({
            "corp_code": (item.findtext("corp_code") or "").strip(),
            "corp_name": (item.findtext("corp_name") or "").strip(),
            "stock_code": (item.findtext("stock_code") or "").strip(),
            "modify_date": (item.findtext("modify_date") or "").strip(),
        })
    return pd.DataFrame(rows)


def resolve_company() -> dict[str, str]:
    df = download_corp_code()
    target = CONFIG["company_name"]
    exact = df[df["corp_name"].eq(target)]
    if exact.empty:
        exact = df[df["corp_name"].str.replace(" ", "", regex=False).eq(target.replace(" ", ""))]
    if exact.empty:
        candidates = df[df["corp_name"].str.contains(target, na=False)].head(10)
        raise RuntimeError(f"회사를 찾지 못했습니다. 후보: {candidates[['corp_name','corp_code']].to_dict('records')}")
    row = exact.iloc[0]
    return row.to_dict()


def norm_num(value: Any) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    s = str(value).strip().replace(",", "")
    if s in {"", "-", "–", "—", "nan", "None"}:
        return None
    s = s.replace("(", "-").replace(")", "")
    s = re.sub(r"[^0-9.\-]", "", s)
    if s in {"", "-", "."}:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def pick_amount(rows: list[dict[str, Any]], aliases: list[str]) -> float | None:
    clean_aliases = [a.replace(" ", "") for a in aliases]
    ranked = []
    for row in rows:
        name = str(row.get("account_nm", ""))
        compact = name.replace(" ", "")
        score = 0
        for i, alias in enumerate(clean_aliases):
            if compact == alias:
                score = 100 - i
                break
            if alias in compact:
                score = max(score, 50 - i)
        if score:
            ranked.append((score, row))
    if not ranked:
        return None
    ranked.sort(key=lambda x: x[0], reverse=True)
    return norm_num(ranked[0][1].get("thstrm_amount"))


def fetch_financials(corp_code: str, year: int, report_code: str, report_type: str) -> tuple[list[dict[str, Any]], str]:
    last_error = None
    for fs_div in [CONFIG["preferred_fs_div"], CONFIG["fallback_fs_div"]]:
        try:
            data = get_json(
                f"{BASE}/fnlttSinglAcntAll.json",
                {
                    "crtfc_key": API_KEY,
                    "corp_code": corp_code,
                    "bsns_year": str(year),
                    "reprt_code": report_code,
                    "fs_div": fs_div,
                },
            )
            rows = data.get("list", [])
            if rows:
                return rows, fs_div
        except Exception as exc:
            last_error = exc
    if last_error:
        raise last_error
    return [], CONFIG["preferred_fs_div"]


def main() -> None:
    require_key()
    company = resolve_company()
    (DATA_DIR / "company.json").write_text(json.dumps(company, ensure_ascii=False, indent=2), encoding="utf-8")

    current_year = pd.Timestamp.now(tz="Asia/Seoul").year
    start_year = max(int(CONFIG["start_year"]), int(CONFIG["dart_financial_data_start_year"]))
    financial_rows: list[dict[str, Any]] = []
    filings: list[dict[str, Any]] = []

    for year in range(start_year, current_year + 1):
        for report_type, report_code in PERIODS:
            try:
                rows, fs_div = fetch_financials(company["corp_code"], year, report_code, report_type)
            except Exception as exc:
                print(f"[WARN] {year} {report_type}: {exc}")
                continue
            if not rows:
                continue

            first = rows[0]
            rcept_no = first.get("rcept_no", "")
            filing_url = f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}" if rcept_no else ""
            filings.append({
                "year": year,
                "period": report_type,
                "reprt_code": report_code,
                "fs_div": fs_div,
                "rcept_no": rcept_no,
                "filing_url": filing_url,
            })

            values = {k: pick_amount(rows, v) for k, v in ALIASES.items()}
            financial_rows.append({
                "year": year,
                "period": report_type,
                "reprt_code": report_code,
                "fs_div": fs_div,
                "corp_code": company["corp_code"],
                "corp_name": company["corp_name"],
                "rcept_no": rcept_no,
                "filing_url": filing_url,
                **values,
            })

    df = pd.DataFrame(financial_rows)
    if not df.empty:
        df = df.sort_values(["year", "period"]).drop_duplicates(["year", "period"], keep="last")
    else:
        df = pd.DataFrame(columns=["year", "period"] + list(ALIASES))
    df.to_csv(DATA_DIR / "financials.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(filings).to_csv(DATA_DIR / "filings.csv", index=False, encoding="utf-8-sig")
    print(f"Saved {len(df)} financial periods and {len(filings)} filings.")


if __name__ == "__main__":
    main()
