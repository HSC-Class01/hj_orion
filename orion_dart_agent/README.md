# Orion DART Financial Analysis Agent

> [![🔗 대시보드 바로가기](https://img.shields.io/badge/%F0%9F%94%97-%EB%8C%80%EC%8B%9C%EB%B3%B4%EB%93%9C%20%EB%B0%94%EB%A1%9C%EA%B0%80%EA%B8%B0-2563eb?style=for-the-badge)](https://HSC-Class01.github.io/orion-dart-agent/)

오리온의 OpenDART 공시와 재무제표를 수집해 주요 재무 수치·재무비율을 계산하고 GitHub Pages 대시보드로 보여주는 프로젝트입니다.

## 주요 기능
- 사업보고서(연간), 반기보고서, 1분기·3분기 보고서 수집
- 2010년부터 수집을 시도하되, OpenDART 구조화 재무제표 API에서 제공되지 않는 과거 수치는 임의 생성하지 않고 누락으로 유지
- 매월 1일(한국시간) 자동 갱신 검사, 수동 실행 지원
- 연결재무제표(CFS)를 우선 사용하고 없으면 별도재무제표(OFS)를 사용하며, 기준을 데이터에 명시
- 매출액·매출원가·매출총이익·영업이익·당기순이익·자산·부채·자본·현금및현금성자산·재고자산·영업활동현금흐름 및 재무비율 계산
- Annual / Half-year / Quarterly 테이블, 그래프, 국내 peer firms 목록 제공

## 1. OpenDART API 키 설정
1. [OpenDART](https://opendart.fss.or.kr/)에 가입하고 인증키를 발급받습니다.
2. GitHub 저장소에서 **Settings → Secrets and variables → Actions → New repository secret**으로 이동합니다.
3. Name은 `DART_API_KEY`, Secret에는 발급받은 키를 입력하고 저장합니다.
4. API 키를 코드, README, 커밋에 직접 입력하지 마세요.

## 2. GitHub에 업로드
1. GitHub에서 저장소를 만듭니다. 기본 예시는 `HSC-Class01/orion-dart-agent`입니다.
2. 압축을 풀고 프로젝트 안의 파일·폴더를 저장소 루트에 업로드합니다.
3. `.github/workflows` 폴더는 GitHub Actions가 동작하는 데 필요하므로 반드시 포함합니다. 이 폴더만 숨김 폴더이지만 의도적으로 포함되어 있습니다. `.DS_Store`, `__MACOSX`, 기타 불필요한 숨김 파일은 없습니다.
4. README와 `dashboard-badge.svg`의 Pages URL에 저장소 이름이 다르면 실제 URL로 바꿉니다.

## 3. GitHub Pages 배포
1. 저장소의 **Settings → Pages**로 이동합니다.
2. Build and deployment의 Source를 **GitHub Actions**로 설정합니다.
3. **Actions** 탭에서 `Update Orion DART data`를 수동 실행합니다. 최초 실행은 데이터가 없어도 dashboard 배포용 파일을 생성합니다.
4. `Deploy dashboard to GitHub Pages` 워크플로가 성공하면 `https://HSC-Class01.github.io/orion-dart-agent/`에서 확인합니다.
5. 저장소 오른쪽 **About → 톱니바퀴(Edit repository details) → Website**에 위 대시보드 URL을 넣고 저장합니다.

## 4. 자동 업데이트 일정
GitHub cron은 UTC 기준이므로 매일 15:05 UTC에 확인 작업을 실행합니다. 스크립트가 `Asia/Seoul` 날짜를 확인해 한국시간 매월 1일에만 공시를 수집·갱신합니다. `workflow_dispatch`로 언제든 수동 실행할 수 있습니다. GitHub의 cron은 부하에 따라 실행이 지연될 수 있습니다.

## 5. 수집 및 분석 범위
- 보고서 코드: 사업보고서 `11011`, 반기보고서 `11012`, 1분기 `11013`, 3분기 `11014`
- 재무제표: 연결 `CFS` 우선, 불가능할 경우 별도 `OFS`를 사용하고 기준을 표시
- 재무비율: 매출성장률, 매출총이익률, 영업이익률, 순이익률, 부채비율, 자기자본비율, ROA, ROE
- ROA·ROE는 가능하면 기초·기말 평균 자산/자본을 분모로 사용합니다.
- OpenDART API의 제공 범위·기업의 공시 형태에 따라 2010~2014년 또는 특정 기간 수치는 없을 수 있습니다. 누락 값은 빈칸으로 표시합니다.

## 6. 국내 Peer Firms
비교 후보는 롯데웰푸드, 크라운제과, 농심, 삼양식품입니다. 식품 업종 내 비교 후보이며 사업 포트폴리오와 회계 기준이 완전히 같지는 않으므로 참고용으로 해석하세요. 이 프로젝트의 기본 테이블은 기업명·업종·DART 검색 링크를 제공하며, 피어 기업 수치까지 자동 비교하려면 각 기업의 corp_code 수집 설정을 추가해야 합니다.

## 폴더 구조
```text
README.md
requirements.txt
config/settings.json
src/dart_crawler.py
src/build_dashboard_data.py
dashboard/index.html
dashboard/data/financials.json
data/raw/
data/processed/
assets/dashboard-badge.svg
.github/workflows/update_data.yml
.github/workflows/pages.yml
```

## 문제 해결
- `DART_API_KEY` 오류: Actions Secrets의 이름과 값 확인
- Pages 404: Settings → Pages가 GitHub Actions인지, Pages workflow가 성공했는지 확인
- 데이터가 비어 있음: 해당 연도·보고서의 공시 여부, OpenDART API 제공 범위, API 응답의 `status`/`message` 확인
- Actions workflow 오류: Actions 로그의 첫 번째 실패 단계 확인; Python 버전은 3.11, 의존성은 `requirements.txt`로 고정합니다.
