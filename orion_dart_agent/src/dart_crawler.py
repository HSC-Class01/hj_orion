from __future__ import annotations
import io, json, os, re, sys, zipfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
API = "https://opendart.fss.or.kr/api"
KEY = os.getenv("DART_API_KEY", "").strip()
CONFIG = json.loads((ROOT / "config/settings.json").read_text(encoding="utf-8"))
RAW = ROOT / "data/raw"
OUT = ROOT / "data/processed/financials.csv"
RAW.mkdir(parents=True, exist_ok=True)
OUT.parent.mkdir(parents=True, exist_ok=True)

if not KEY:
    raise SystemExit("DART_API_KEY 환경 변수가 없습니다. GitHub Actions Secrets에 등록하세요.")

session = requests.Session()
session.headers.update({"User-Agent": "orion-dart-financial-analysis/1.0"})
retry = Retry(
    total=2,
    connect=2,
    read=2,
    status=2,
    backoff_factor=0.8,
    status_forcelist=(429, 500, 502, 503, 504),
    allowed_methods=frozenset(["GET"]),
    respect_retry_after_header=True,
)
session.mount("https://", HTTPAdapter(max_retries=retry))

def get_json(endpoint, params):
    p = {**params, "crtfc_key": KEY}
    r = session.get(f"{API}/{endpoint}", params=p, timeout=(15, 45))
    r.raise_for_status()
    data = r.json()
    status = str(data.get("status", ""))
    if status not in ("000", "013"):
        # 013 means no data; caller can continue to the next filing.
        if status == "013": return data
        raise RuntimeError(f"OpenDART {endpoint}: status={status}, message={data.get('message')}")
    return data

def resolve_corp_code():
    configured = str(CONFIG.get("corp_code", "")).strip()
    if configured:
        return configured
    path = RAW / "corpCode.xml"
    if not path.exists():
        r = session.get(f"{API}/corpCode.xml", params={"crtfc_key": KEY}, timeout=(15, 45))
        r.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            xml = z.read("CORPCODE.xml")
        path.write_bytes(xml)
    df = pd.read_xml(path, xpath="//list", dtype={"corp_code": str, "stock_code": str}, parser="etree")
    matches = df[df["corp_name"].astype(str).str.strip().eq(CONFIG["company_name"])]
    if matches.empty:
        matches = df[df["corp_name"].astype(str).str.contains("오리온", na=False)]
    # Orion Holdings and Orion are different issuers; exact company name is required where possible.
    if matches.empty:
        raise RuntimeError("corpCode.xml에서 오리온을 찾지 못했습니다.")
    exact = matches[matches["corp_name"].astype(str).str.strip().eq("오리온")]
    row = (exact.iloc[0] if not exact.empty else matches.iloc[0])
    code = str(row["corp_code"]).zfill(8)
    print(f"Resolved corp_code={code}, corp_name={row['corp_name']}")
    return code

def filing_list(corp, year, reprt_code):
    # DART list.json is filtered by receipt date, not fiscal year. Annual
    # reports are normally filed in the following calendar year.
    filing_year = year + 1 if reprt_code == "11011" else year
    data = get_json("list.json", {
        "corp_code": corp,
        "bgn_de": f"{filing_year}0101",
        "end_de": f"{filing_year}1231",
        "pblntf_ty": "A",
        "page_no": 1,
        "page_count": 100,
        "last_reprt_at": "Y",
    })
    rows = data.get("list", []) or []
    candidates = []
    for item in rows:
        title = str(item.get("report_nm", ""))
        if reprt_code == "11011" and "사업보고서" not in title:
            continue
        if reprt_code == "11012" and "반기보고서" not in title:
            continue
        if reprt_code in ("11013", "11014"):
            if "분기보고서" not in title:
                continue
            period_match = re.search(r"\((\d{4})\.(\d{2})\)", title)
            month = int(period_match.group(2)) if period_match else 0
            if month == 0:
                receipt = str(item.get("rcept_dt", ""))
                month = int(receipt[4:6]) if len(receipt) >= 6 else 0
            if reprt_code == "11013" and month not in (3, 4, 5, 6):
                continue
            if reprt_code == "11014" and month not in (9, 10, 11, 12):
                continue
        candidates.append(item)
    if not candidates:
        return None
    return max(candidates, key=lambda item: str(item.get("rcept_dt", "")))
def parse_amount(v):
    if v is None: return None
    s = str(v).strip().replace(",", "")
    if not s or s in ("-", "－", "N/A"): return None
    try: return float(s)
    except ValueError: return None

def choose_account(rows, keywords):
    # Prefer exact Korean account labels; fallback to substring.
    for kw in keywords:
        exact = [x for x in rows if str(x.get("account_nm","")).strip() == kw]
        if exact:
            val = parse_amount(exact[0].get("thstrm_amount"))
            if val is not None: return val, exact[0].get("account_nm")
    for kw in keywords:
        found = [x for x in rows if kw in str(x.get("account_nm", ""))]
        if found:
            val = parse_amount(found[0].get("thstrm_amount"))
            if val is not None: return val, found[0].get("account_nm")
    return None, ""

def fetch_accounts(corp, year, reprt_code):
    data = get_json("fnlttSinglAcntAll.json", {"corp_code":corp,"bsns_year":str(year),"reprt_code":reprt_code,"fs_div":"CFS"})
    rows = data.get("list", []) or []
    fs_div = "CFS"
    if not rows:
        data = get_json("fnlttSinglAcntAll.json", {"corp_code":corp,"bsns_year":str(year),"reprt_code":reprt_code,"fs_div":"OFS"})
        rows = data.get("list", []) or []
        fs_div = "OFS"
    if not rows: return None
    # Avoid mixing statements: use one fs_div per filing and map account names from that set only.
    metrics = {
      "revenue": ["매출액","수익(매출액)","영업수익"],
      "cost_of_sales": ["매출원가"],
      "gross_profit": ["매출총이익"],
      "operating_income": ["영업이익","영업이익(손실)"],
      "net_income": ["당기순이익","당기순이익(손실)","분기순이익","반기순이익"],
      "assets": ["자산총계"], "liabilities": ["부채총계"], "equity": ["자본총계"],
      "cash": ["현금및현금성자산","현금및현금성자산(현금및현금성자산)"],
      "inventory": ["재고자산"], "operating_cash_flow": ["영업활동현금흐름","영업활동으로 인한 현금흐름"]
    }
    out = {}
    for key, labels in metrics.items(): out[key], out[key+"_account"] = choose_account(rows, labels)
    # The statement API's thstrm_amount is the reported period amount. Preserve raw rows for audit.
    raw_path = RAW / f"{year}_{reprt_code}_{fs_div}.json"
    raw_path.write_text(json.dumps({"status":data.get("status"),"corp_code":corp,"year":year,"reprt_code":reprt_code,"fs_div":fs_div,"list":rows},ensure_ascii=False,indent=2),encoding="utf-8")
    filing = filing_list(corp, year, reprt_code)
    return {"year":year,"report_code":reprt_code,"report_type":{"11011":"Annual","11012":"Half-year","11013":"Quarterly Q1","11014":"Quarterly Q3"}[reprt_code],"corp_code":corp,"fs_div":fs_div,"receipt_no":(filing or {}).get("rcept_no",""),"report_name":(filing or {}).get("report_nm",""),"receipt_date":(filing or {}).get("rcept_dt",""),**out}

def main():
    force = "--force" in sys.argv
    now = datetime.now(ZoneInfo("Asia/Seoul"))
    if not force and now.day != 1:
        print(f"Skip: Korea date is {now.date()}, scheduled collection runs on day 1. Use --force for manual collection.")
        return
    corp = resolve_corp_code()
    existing = pd.read_csv(OUT, dtype={"report_code":str,"corp_code":str,"receipt_no":str,"receipt_date":str}) if OUT.exists() else pd.DataFrame()
    old_keys = set()
    if not existing.empty:
        old_keys = set(existing.apply(lambda r:f"{int(r['year'])}-{r['report_code']}",axis=1))
    rows=[]
    # Attempt all years since 2010; unavailable API periods are omitted rather than fabricated.
    for year in range(int(CONFIG.get("start_year",2010)), now.year+1):
        for code in ("11011","11012","11013","11014"):
            key=f"{year}-{code}"
            # Refresh current year and current/previous year for amendments; keep prior saved rows otherwise.
            if key in old_keys and "--refresh-all" not in sys.argv and year < now.year-1: continue
            try:
                item=fetch_accounts(corp,year,code)
                if item: rows.append(item); print(f"Collected {key} ({item['fs_div']})")
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                raise RuntimeError(f"OpenDART connection failed while collecting {key}; stopping early instead of repeating a network outage for every period.") from e
            except Exception as e:
                print(f"Warning: {key} skipped: {e}")
    new=pd.DataFrame(rows)
    if not existing.empty:
        existing=existing[~existing.apply(lambda r:f"{int(r['year'])}-{r['report_code']}",axis=1).isin(set(new.apply(lambda r:f"{int(r['year'])}-{r['report_code']}",axis=1)) if not new.empty else set())]
        new=pd.concat([existing,new],ignore_index=True) if not new.empty else existing
    if not new.empty:
        new=new.sort_values(["year","report_code"]).drop_duplicates(["year","report_code"],keep="last")
        new.to_csv(OUT,index=False,encoding="utf-8-sig")
        print(f"Saved {len(new)} rows to {OUT}")
    else:
        print("No structured financial statement data returned. Existing dataset was preserved.")

if __name__ == "__main__": main()
