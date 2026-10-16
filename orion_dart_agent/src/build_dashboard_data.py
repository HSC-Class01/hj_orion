from pathlib import Path
import json, math
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
source=ROOT/"data/processed/financials.csv"
target=ROOT/"dashboard/data/financials.json"
target.parent.mkdir(parents=True,exist_ok=True)
config=json.loads((ROOT/"config/settings.json").read_text(encoding="utf-8"))
peers=config.get("peer_firms",[])
if source.exists() and source.stat().st_size:
    df=pd.read_csv(source,dtype={"report_code":str,"corp_code":str,"receipt_no":str,"receipt_date":str})
else: df=pd.DataFrame()
# pandas NaN -> JSON null
records=[]
if not df.empty:
    df=df.sort_values(["year","report_code"])
    for _,r in df.iterrows():
        x={k:(None if pd.isna(v) else v) for k,v in r.to_dict().items()}
        for k in ("year",):
            if x.get(k) is not None: x[k]=int(x[k])
        for k in ("revenue","cost_of_sales","gross_profit","operating_income","net_income","assets","liabilities","equity","cash","inventory","operating_cash_flow"):
            if x.get(k) is not None:
                try: x[k]=float(x[k])
                except (ValueError,TypeError): x[k]=None
        records.append(x)
# Calculate period-over-period year comparisons for matching report categories.
bykey={(int(x["year"]),str(x.get("report_code"))):x for x in records}
for x in records:
    prev=bykey.get((int(x["year"])-1,str(x["report_code"])))
    rev=x.get("revenue"); prevrev=prev.get("revenue") if prev else None
    x["revenue_growth_pct"]=(rev-prevrev)/abs(prevrev)*100 if rev is not None and prevrev not in (None,0) else None
    for metric,label in (("gross_profit","gross_margin_pct"),("operating_income","operating_margin_pct"),("net_income","net_margin_pct")):
        val=x.get(metric); x[label]=val/rev*100 if val is not None and rev not in (None,0) else None
    liab=x.get("liabilities"); eq=x.get("equity"); assets=x.get("assets")
    x["debt_ratio_pct"]=liab/eq*100 if liab is not None and eq not in (None,0) else None
    x["equity_ratio_pct"]=eq/assets*100 if eq is not None and assets not in (None,0) else None
    passets=prev.get("assets") if prev else None; pequity=prev.get("equity") if prev else None
    avg_assets=(assets+passets)/2 if assets is not None and passets is not None else assets
    avg_equity=(eq+pequity)/2 if eq is not None and pequity is not None else eq
    x["roa_pct"]=x.get("net_income")/avg_assets*100 if x.get("net_income") is not None and avg_assets not in (None,0) else None
    x["roe_pct"]=x.get("net_income")/avg_equity*100 if x.get("net_income") is not None and avg_equity not in (None,0) else None
if not records:
    raise SystemExit(f"No financial records found in {source}; refusing to publish an empty dashboard.")
payload={"company":"오리온","currency_unit":"KRW","amount_unit":"API 원 단위(차트에서 억 원 환산)","generated_at":pd.Timestamp.now(tz="Asia/Seoul").isoformat(),"records":records,"peers":peers,"notes":["OpenDART API가 제공하지 않는 기간의 값은 null로 유지합니다.","연결재무제표(CFS) 우선, 없으면 별도재무제표(OFS)를 사용합니다. 각 행의 fs_div를 확인하세요.","분기·반기 보고서의 당기 금액은 보고서별 표기 기준을 따릅니다. 연간 합계와 직접 비교할 때는 주의하세요."]}
target.write_text(json.dumps(payload,ensure_ascii=False,indent=2,default=str,allow_nan=False),encoding="utf-8")
print(f"Wrote {target} ({len(records)} records)")
