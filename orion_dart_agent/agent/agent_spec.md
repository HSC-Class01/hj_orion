# Agent Specification — Orion DART

## Objective
Collect Orion's public financial filings from OpenDART, normalize key statement items, calculate standard financial ratios, and publish static JSON for a GitHub Pages dashboard.

## Data rules
- Target issuer is `오리온`, not `오리온홀딩스`. Verify resolved corporation name in logs.
- Attempt report years from 2010 onward. Missing API periods are not synthesized.
- Annual: `11011`; half-year: `11012`; first-quarter: `11013`; third-quarter: `11014`.
- Prefer consolidated statements (`CFS`), fallback to separate statements (`OFS`) only when consolidated rows are unavailable; never merge values from the two bases in one filing.
- Store raw API rows by year/report/fs_div for traceability.
- Key values: revenue, cost of sales, gross profit, operating income, net income, total assets, total liabilities, total equity, cash and cash equivalents, inventory, operating cash flow.
- Ratios: revenue growth, gross margin, operating margin, net margin, debt ratio, equity ratio, ROA, ROE.
- Guard missing and zero denominators. ROA/ROE use average assets/equity when previous-year matching data is available.

## Schedule
GitHub Actions checks daily at 00:05 Korea time. Data collection runs on day 1 of the Korean calendar, or on manual dispatch with `--force`.

## Outputs
- `data/raw/`: raw statement response records
- `data/processed/financials.csv`: normalized rows
- `dashboard/data/financials.json`: dashboard-ready data
- `dashboard/index.html`: static dashboard

## Operational limits
OpenDART API availability and filings vary by year. Structured financial statement endpoints may not return data for all years back to 2010. Always retain missing values as null/blank and preserve prior data when no new response is returned.
