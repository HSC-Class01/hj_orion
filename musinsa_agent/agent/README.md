# Musinsa DART Financial Analysis Agent

This project collects Musinsa financial information from OpenDART, normalizes major financial statement items, calculates financial ratios, and publishes a static GitHub Pages dashboard.

## Agent flow

1. Resolve Musinsa `corp_code` from OpenDART `corpCode.xml`.
2. Collect annual, half-year, Q1 and Q3 financial statements.
3. Prefer consolidated statements (`CFS`) and fall back to separate statements (`OFS`) when consolidated data are unavailable.
4. Save normalized financial data and filing metadata under `data/`.
5. Calculate growth, profitability, cash-flow, leverage and return ratios.
6. Generate `dashboard/data/*.json` for the static dashboard.
7. GitHub Actions runs the updater automatically and deploys GitHub Pages.

## Important date limitation

The requested collection start is 2010. OpenDART's structured `fnlttSinglAcntAll` financial statement API currently provides financial information from 2015 onward. The agent therefore keeps `start_year=2010` as the project scope, but structured financial extraction begins when the API provides the relevant fiscal year. This avoids inventing 2010–2014 values.

## Report coverage

- Annual report: 11011
- Half-year report: 11012
- Q1 report: 11013
- Q3 report: 11014

OpenDART does not provide a separate Q2 report code; the half-year report is the H1 filing.
