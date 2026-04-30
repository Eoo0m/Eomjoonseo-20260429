import json
import asyncio
import os
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

TAGS = ["맛", "건강", "가성비", "다이어트", "조리 편의성", "가족/아이용", "재구매 의사"]

SYSTEM_PROMPT = """당신은 식품 리뷰 분석 전문가입니다.
주어진 제품 리뷰들을 분석하여 아래 7개 태그에 해당하는 대표 리뷰 문장을 추출해주세요.

태그 (넓게 해석하세요):
1. 맛 - 맛, 풍미, 식감, 향, 맛있다, 달다, 짜다, 고소하다, 매콤하다 등 맛 관련 모든 언급
2. 건강 - 건강, 영양, 나트륨, 칼로리, 성분, 유기농, 무첨가, 비타민, 몸에 좋다, 건강에 신경, 영양가 등
3. 가성비 - 가격, 가성비, 할인, 경제적, 저렴, 싸다, 합리적, 묶음 구매, 대용량, 양이 많다 등
4. 다이어트 - 다이어트, 체중 관리, 칼로리 조절, 가볍게 먹다, 부담 없이, 저칼로리, 제로, 당 조절, 살빼다, 간식 대용, 야식 대신, 포만감 대비 칼로리 낮다, 건강하게 먹으려고 등. 직접적인 다이어트 언급 외에도 "가볍게 한 끼", "부담 없는 간식" 같은 표현도 포함
5. 조리 편의성 - 조리 방법, 간편함, 시간 절약, 끓이기만 하면, 전자레인지, 간단하게, 바쁠 때, 혼자 먹기, 비상식량, 바로 먹을 수 있다, 보관 편리 등
6. 가족/아이용 - 가족, 아이, 아이들, 온 가족, 아들, 딸, 엄마, 아빠, 부모님, 집에서 가족과, 아이가 좋아한다, 아이 간식, 가족 간식, 집에서 다같이, 자녀, 손주, 우리 식구, 가족 식사 등. 가족 구성원과 함께 먹는 것에 대한 모든 언급 포함
7. 재구매 의사 - 재구매, 또 사고 싶다, 다시 주문, 또 살 거다, 계속 구매, 다 먹으면 또, 항상 사는, 꾸준히 구매, 또 시킬 예정 등

중요 규칙:
- 모든 7개 태그에 대해 최대한 적극적으로 해당 문장을 찾으세요.
- 특히 "다이어트"와 "가족/아이용" 태그는 넓게 해석하여, 간접적 언급도 포함하세요.
- 각 태그당 가장 대표적인 리뷰 문장을 1~3개 추출하세요.
- 문장은 원문 그대로 유지하되, 너무 길면 핵심만 30자 내외로 다듬어주세요.
- 해당 태그에 맞는 내용이 정말 전혀 없을 때만 빈 배열로 반환하세요.
- 반드시 JSON 형식으로만 응답하세요."""

USER_PROMPT_TEMPLATE = """제품명: {title}

리뷰들:
{reviews}

위 리뷰들을 분석하여 아래 JSON 형식으로 응답해주세요. 모든 태그에 최대한 문장을 채워주세요:
{{
  "맛": ["문장1", "문장2"],
  "건강": ["문장1"],
  "가성비": ["문장1", "문장2"],
  "다이어트": ["문장1"],
  "조리 편의성": ["문장1"],
  "가족/아이용": ["문장1"],
  "재구매 의사": ["문장1"]
}}"""


async def classify_product(product, semaphore, idx, total):
    async with semaphore:
        title = product["title"]
        reviews = product["reviews"]

        # 리뷰 텍스트 합치기 (너무 길면 앞부분만)
        review_texts = []
        total_chars = 0
        for r in reviews:
            text = r.get("text", "")
            if total_chars + len(text) > 15000:  # ~15K chars limit per product
                break
            review_texts.append(text)
            total_chars += len(text)

        combined_reviews = "\n---\n".join(review_texts)

        try:
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": USER_PROMPT_TEMPLATE.format(
                        title=title, reviews=combined_reviews
                    )},
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=500,
            )

            tags = json.loads(response.choices[0].message.content)
            # Ensure all tags exist
            for tag in TAGS:
                if tag not in tags:
                    tags[tag] = []

            print(f"[{idx+1}/{total}] ✓ {title}")
            return {
                "title": title,
                "main_image": product["main_image"],
                "url": product["url"],
                "tags": tags,
            }
        except Exception as e:
            print(f"[{idx+1}/{total}] ✗ {title}: {e}")
            return {
                "title": title,
                "main_image": product["main_image"],
                "url": product["url"],
                "tags": {tag: [] for tag in TAGS},
            }


async def main():
    with open("output/products.json", "r", encoding="utf-8") as f:
        products = json.load(f)

    # 리뷰가 있는 제품만 필터링
    products_with_reviews = [p for p in products if p["reviews"] and p["title"]]
    print(f"분류 대상: {len(products_with_reviews)}개 제품")

    semaphore = asyncio.Semaphore(10)  # 동시 10개 요청
    total = len(products_with_reviews)

    tasks = [
        classify_product(p, semaphore, i, total)
        for i, p in enumerate(products_with_reviews)
    ]
    results = await asyncio.gather(*tasks)

    # 결과 저장
    output_path = "output/classified_products.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n완료! {output_path}에 저장됨")

    # 통계
    tag_counts = {tag: 0 for tag in TAGS}
    for r in results:
        for tag in TAGS:
            if r["tags"].get(tag):
                tag_counts[tag] += 1
    print("\n태그별 제품 수:")
    for tag, count in tag_counts.items():
        print(f"  {tag}: {count}개 제품")


if __name__ == "__main__":
    asyncio.run(main())
