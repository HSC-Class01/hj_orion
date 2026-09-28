# Musinsa DART Financial Analysis

<a href="https://hsc-class01.github.io/musinsa_dart/"><img src="assets/dashboard-badge.svg" alt="🔗 대시보드 바로가기" width="260"></a>

> OpenDART의 무신사 사업보고서·반기보고서·분기보고서 재무수치를 수집하고 재무비율을 계산해 GitHub Pages에서 시각화하는 자동화 프로젝트입니다.

## Dashboard

**🔗 대시보드 바로가기:** https://hsc-class01.github.io/musinsa_dart/

The dashboard presents:

- Top-level visual figures: revenue, operating income, net income, operating cash flow
- Profitability and financial-structure charts
- **Annual / Half-year / Quarterly** tables
- Revenue growth, operating margin, net margin, debt ratio, equity ratio, ROA and ROE
- Domestic peer-firm reference table at the bottom
- DART receipt numbers and filing links for traceability

## Automated update

The update workflow checks the Korean date every day at 00:15 KST and performs the DART refresh only when the KST date is the **1st of the month**. This avoids the UTC/KST month-boundary problem that can occur with a simple `1 * * *` cron expression.

A manual update is also available from **Actions → Update Musinsa DART data → Run workflow**.

## OpenDART API

The project uses the OpenDART API endpoint for single-company full financial statements:

- `fnlttSinglAcntAll.json`
- Annual: `11011`
- Half-year: `11012`
- Q1: `11013`
- Q3: `11014`

OpenDART currently documents structured financial statement availability from **2015 onward** for this API. The project scope remains configured from 2010 as requested, but it does not fabricate structured values for years the API does not provide.

## API key setup

1. Open https://opendart.fss.or.kr/
2. Sign in and issue an OpenDART API key.
3. In the GitHub repository go to **Settings → Secrets and variables → Actions**.
4. Create a repository secret named exactly:

```text
DART_API_KEY
```

5. Paste the 40-character DART key as the secret value.
6. Run the workflow manually once to verify the first collection.

### Local run

```bash
export DART_API_KEY="YOUR_DART_API_KEY"
python -m pip install -r requirements.txt
python src/dart_crawler.py
python src/build_dashboard_data.py
```

Windows PowerShell:

```powershell
$env:DART_API_KEY="YOUR_DART_API_KEY"
python -m pip install -r requirements.txt
python src/dart_crawler.py
python src/build_dashboard_data.py
```

**Do not put the API key directly into Python, JSON, YAML, README, or committed files.**

## GitHub Pages setup

1. Push this project to the repository's `main` branch.
2. Open **Settings → Pages**.
3. Under **Build and deployment → Source**, select **GitHub Actions**.
4. The `pages.yml` workflow deploys only the `dashboard/` directory.

GitHub's current Pages custom-workflow flow uses `actions/configure-pages`, `actions/upload-pages-artifact`, and `actions/deploy-pages`; the included workflow follows that pattern.

## GitHub repository About section

Set the repository's About website to:

```text
https://hsc-class01.github.io/musinsa_dart/
```

Recommended description:

```text
OpenDART-based Musinsa financial analysis agent and GitHub Pages dashboard.
```

The repository About section itself requires repository settings/API access; it is not controlled by the Pages workflow.

## Project structure

```text
.
├── README.md
├── requirements.txt
├── config/
│   └── settings.json
├── agent/
│   ├── README.md
│   ├── agent_spec.md
│   └── agent_prompt.md
├── src/
│   ├── dart_crawler.py
│   └── build_dashboard_data.py
├── data/
│   ├── raw/
│   └── .gitkeep
├── dashboard/
│   ├── index.html
│   └── data/
├── assets/
│   └── dashboard-badge.svg
└── .github/
    └── workflows/
        ├── update_data.yml
        └── pages.yml
```

## Major financial data

The supplied financial-statement / financial-ratio guide emphasizes a practical analysis sequence of **revenue growth → profitability → cash flow → leverage → return analysis**. The agent therefore extracts and derives:

| Category | Metrics |
|---|---|
| Growth | Revenue, revenue growth |
| Profitability | Operating income, net income, operating margin, net margin |
| Cash flow | Operating cash flow, operating-cash-flow margin |
| Financial structure | Total assets, total liabilities, total equity, debt ratio, equity ratio |
| Return | ROA, ROE |
| Supporting balance-sheet items | Cash & cash equivalents, inventory |

## Domestic peer firms

The peer table is a **business-model reference list**, not an automatic financial comparison dataset. It can be edited in `config/settings.json`.

| Peer firm | Focus | Note |
|---|---|---|
| 카카오스타일 (지그재그) | 패션·커머스 플랫폼 | 국내 패션 플랫폼 |
| 에이블리 | 패션·커머스 플랫폼 | 스타일 커머스 플랫폼 |
| 29CM | 셀렉트숍·패션 커머스 | 취향 기반 커머스 |
| W컨셉 | 패션 커머스 | 디자이너 패션 중심 |
| 브랜디 | 패션·커머스 플랫폼 | 온라인 패션 커머스 |
| 쿠팡 | 종합 이커머스 | 국내 온라인 유통 대형 사업자 |

## Data integrity rules

- Missing data are kept as `null`, not zero.
- The crawler prefers consolidated statements (`CFS`) and falls back to separate statements (`OFS`) when necessary.
- Filing receipt numbers and DART viewer URLs are retained.
- A failed API response is not silently converted into an empty financial result.
- The update workflow commits only changed `data/` and `dashboard/data/` files.

## License / source note

Financial data are sourced from OpenDART. Check the terms and usage limits of the OpenDART service before redistributing or making high-volume requests.
