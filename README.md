# REVIEWPICK - AI 리뷰 큐레이션 쇼핑몰

## 서비스 개요
쿠팡 식품 100개 제품의 리뷰 10,000개를 크롤링하고, GPT로 리뷰를 태그별로 분류하여 사용자가 원하는 관점(맛/가성비/건강 등)으로 리뷰를 탐색할 수 있는 웹 서비스.
자연어 검색 시 GPT가 의도를 분석해 음식 카테고리 필터링 + 리뷰 태그 하이라이트를 자동 수행.
프론트엔드 React(Next.js) / 백엔드 Node.js(API Routes) / AI ChatGPT API / 호스팅 Vercel.

## 크롤링 방법
Chrome을 디버그 모드(`--remote-debugging-port=9222`)로 실행 후, Playwright가 CDP로 연결하여 기존 로그인 세션을 활용.
쿠팡 카테고리 페이지를 순회하며 제품 URL 120개를 수집하고, 각 제품 페이지에서 제품명/이미지/리뷰(최대 100개)를 스크래핑.
안티봇 대응으로 랜덤 딜레이(3~10초), 마우스 무작위 이동, 점진적 스크롤을 적용.
중간 저장 기능으로 중단 후 이어서 크롤링 가능.

## GPT 전처리
`classify_reviews.py`: 제품별 리뷰를 GPT-4o-mini에 전송하여 7개 태그(맛/건강/가성비/다이어트/조리 편의성/가족·아이용/재구매 의사)별 대표 문장 추출. asyncio로 동시 10개 요청 처리.
`classify_categories.py`: 100개 제품명을 한 번에 GPT에 전송하여 12개 음식 카테고리(라면/과자/음료/신선식품 등)로 분류.

## 에이전트 구조
사용자가 검색창에 자연어 입력 (예: "가성비 좋은 라면") → Next.js API Route(`/api/search`)가 GPT-4o-mini 호출.
GPT가 쿼리를 분석하여 두 가지 결과 반환: ①`food_categories`(음식 카테고리) ②`review_tags`(리뷰 관점).
①로 제품 목록을 필터링하고, ②로 해당 태그의 리뷰를 우선 노출하여 결과 렌더링.
즉, LLM 입력 → 카테고리 필터 함수 + 리뷰 태그 필터 함수 → 프론트엔드 노출.

## 실행
```bash
npm install && echo "OPENAI_API_KEY=sk-xxx" > .env.local && npm run dev
```
