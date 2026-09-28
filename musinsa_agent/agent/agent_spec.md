# Agent specification

## Objective

Maintain a reproducible Musinsa financial dataset and dashboard from OpenDART filings.

## Inputs

- `DART_API_KEY`: GitHub Actions secret containing the 40-character OpenDART API key.
- `config/settings.json`: company, report codes, date scope and peer firms.

## Outputs

- `data/financials.csv`: normalized financial statement values.
- `data/ratios.csv`: calculated financial ratios.
- `data/filings.csv`: report metadata and DART receipt links.
- `dashboard/data/financials.json`: dashboard-ready dataset.
- `dashboard/data/ratios.json`: dashboard-ready ratio dataset.
- `dashboard/data/filings.json`: dashboard-ready filing metadata.

## Major metrics

Revenue, operating income, net income, operating cash flow, total assets, total liabilities, total equity, cash and cash equivalents, inventory, revenue growth, operating margin, net margin, debt ratio, equity ratio, ROA, ROE and operating-cash-flow margin.

The metric set follows the supplied financial-statement / financial-ratio guide's analysis flow: revenue growth, profitability, cash flow, leverage and return analysis.
