# Orion Financial Dashboard

오리온의 OpenDART 공시와 재무제표를 수집·분석하고 GitHub Pages 대시보드로 제공합니다.

- **Dashboard:** https://hsc-class01.github.io/hj_orion/
- **Detailed setup and data notes:** [orion_dart_agent/README.md](orion_dart_agent/README.md)
- **Automation:** GitHub Actions runs monthly and supports manual execution.

To enable data collection, add the OpenDART API key as the repository Actions secret `DART_API_KEY`. Then run **Actions → Update DART Data**. The workflow builds the dashboard JSON and deploys `orion_dart_agent/dashboard` to GitHub Pages.
