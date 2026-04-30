# REVIEWPICK - AI 기반 식품 리뷰 큐레이션 쇼핑몰

크롤링한 쿠팡 식품 리뷰 데이터를 GPT API로 분석하여, 사용자가 원하는 관점(맛/가성비/건강 등)으로 리뷰를 탐색할 수 있는 웹 서비스입니다.

## 프로젝트 개요

| 항목 | 내용 |
|------|------|
| **서비스명** | REVIEWPICK (리뷰픽) |
| **프론트엔드** | Next.js 16 (React, TypeScript, Tailwind CSS) |
| **백엔드** | Next.js API Routes (Node.js 서버리스) |
| **AI** | OpenAI GPT-4o-mini (리뷰 분류 + 검색 의도 분석) |
| **크롤링** | Playwright + Chrome DevTools Protocol |
| **호스팅** | Vercel |
| **데이터** | 쿠팡 식품 100개 제품, 10,000개 리뷰 |

## 전체 아키텍처

```
[크롤링 파이프라인]                    [웹 서비스]

 Chrome Debug Mode                   Next.js (Vercel)
       |                                  |
 Playwright (CDP 연결)               ┌─────┴─────┐
       |                             |           |
 coupang_scraper.py              React UI    API Route
  - 제품 URL 수집 (카테고리 순회)    (page.tsx)  (/api/search)
  - 제품 상세 스크래핑                  |           |
  - 리뷰 100개/제품 수집               |      GPT-4o-mini
  - 이미지 다운로드                    |     (의도 분석)
       |                             |           |
 products.json (원본 데이터)         ┌─┴───────────┴─┐
       |                            |               |
 GPT-4o-mini 분석                음식 카테고리    리뷰 태그
  - classify_reviews.py          필터링          하이라이트
    (7개 리뷰 태그 분류)               |               |
  - classify_categories.py           └───────┬───────┘
    (12개 음식 카테고리 분류)                 |
       |                            제품 그리드 + 리뷰 노출
 classified_products.json
```

## 크롤링 방법 (scripts/)

### 1단계: 제품 URL 수집 (`coupang_scraper.py collect`)
- Chrome을 디버그 모드(`--remote-debugging-port=9222`)로 실행
- Playwright가 CDP(Chrome DevTools Protocol)로 연결하여 기존 브라우저 세션 활용
- 쿠팡 카테고리 페이지를 순회하며 제품 URL 120개 이상 수집
- 안티봇 대응: 랜덤 딜레이(3~7초), 마우스 이동, 점진적 스크롤

### 2단계: 제품 상세 스크래핑 (`coupang_scraper.py scrape`)
- 수집된 URL을 하나씩 방문하며 스크래핑
- 수집 항목: 제품명, 대표 이미지, 상세 이미지, 리뷰(최대 100개/제품)
- 리뷰 페이지네이션 처리 (다음 페이지 버튼 클릭)
- 이어하기 지원: 중간 저장으로 중단 후 재시작 가능
- Access Denied 시 대기 후 재시도

### 3단계: 가격 크롤링 (`scrape_prices.py`)
- 기존 products.json의 URL로 각 제품 페이지 재방문
- `div.sales-price-amount` 등 가격 셀렉터로 가격 추출
- 5개마다 중간 저장

## GPT API 활용 (에이전트 구조)

### 리뷰 태그 분류 (`classify_reviews.py`)
- **입력**: 제품별 리뷰 전체 텍스트 (최대 15,000자)
- **처리**: GPT-4o-mini가 7개 태그별 대표 문장 추출
- **태그**: 맛, 건강, 가성비, 다이어트, 조리 편의성, 가족/아이용, 재구매 의사
- **방식**: asyncio로 동시 10개 요청, 제품당 1회 API 호출
- **출력**: 태그별 대표 리뷰 문장 1~3개

### 음식 카테고리 분류 (`classify_categories.py`)
- **입력**: 100개 제품명 전체를 한 번에 전송
- **처리**: GPT-4o-mini가 12개 카테고리로 분류
- **카테고리**: 라면/면류, 과자/스낵, 음료/생수, 유제품, 커피/차, 신선식품, 냉동/간편식, 양념/소스/오일, 통조림/캔, 빵/베이커리, 시리얼/에너지바, 건강식품/비타민
- **방식**: 1회 API 호출로 전체 분류

### 검색 의도 분석 (`/api/search` API Route)
- **입력**: 사용자 자연어 검색 쿼리 (예: "가성비 좋은 라면")
- **처리**: GPT-4o-mini가 두 가지 함수로 분해
  1. `food_categories` → 음식 카테고리 필터링
  2. `review_tags` → 리뷰 태그 하이라이트
- **출력**: 필터링된 제품 + 관련 리뷰 강조

## 주요 기능

### 태그 기반 리뷰 탐색
- 7개 리뷰 태그 버튼 클릭 시 해당 관점의 리뷰 한 줄이 제품별로 노출
- 해당 태그 리뷰가 없는 제품은 투명도 낮춤

### AI 검색
- 자연어로 검색하면 GPT가 의도를 분석하여 음식 카테고리 + 리뷰 관점을 자동 추출
- 예: "아이 간식 추천" → 카테고리: 과자/스낵 + 태그: 가족/아이용

## 프로젝트 구조

```
reviewpick/
├── scripts/                    # 크롤링 & 분류 스크립트
│   ├── coupang_scraper.py      # 쿠팡 제품/리뷰 크롤러
│   ├── scrape_prices.py        # 가격 크롤러
│   ├── classify_reviews.py     # GPT 리뷰 태그 분류
│   └── classify_categories.py  # GPT 음식 카테고리 분류
├── public/images/              # 제품 이미지 (100개)
├── src/
│   ├── app/
│   │   ├── layout.tsx          # 루트 레이아웃
│   │   ├── page.tsx            # 메인 페이지 (서버 컴포넌트)
│   │   ├── MainContent.tsx     # 검색/태그/그리드 (클라이언트 컴포넌트)
│   │   ├── globals.css         # 글로벌 스타일
│   │   └── api/search/
│   │       └── route.ts        # GPT 검색 API 엔드포인트
│   └── data/
│       └── products.json       # 분류 완료된 제품 데이터
├── .env.local                  # OPENAI_API_KEY (Git 제외)
└── package.json
```

## 실행 방법

### 크롤링 (데이터 수집)
```bash
# Chrome 디버그 모드 실행
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 --user-data-dir=/tmp/coupang_chrome

# 1. 제품 URL 수집
python3 scripts/coupang_scraper.py collect

# 2. 제품 상세 스크래핑 (리뷰 포함)
python3 scripts/coupang_scraper.py scrape

# 3. GPT로 리뷰 태그 분류
python3 scripts/classify_reviews.py

# 4. GPT로 음식 카테고리 분류
python3 scripts/classify_categories.py
```

### 웹 서비스
```bash
npm install
echo "OPENAI_API_KEY=sk-xxx" > .env.local
npm run dev        # 로컬 개발 서버 (http://localhost:3000)
npm run build      # 프로덕션 빌드
```

## 환경 변수

| 변수 | 설명 |
|------|------|
| `OPENAI_API_KEY` | OpenAI API 키 (검색 API에서 사용) |
