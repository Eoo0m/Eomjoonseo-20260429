import json
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

CATEGORIES = [
    "라면/면류",
    "과자/스낵",
    "음료/생수",
    "유제품",
    "커피/차",
    "신선식품",
    "냉동/간편식",
    "양념/소스/오일",
    "통조림/캔",
    "빵/베이커리",
    "시리얼/에너지바",
    "건강식품/비타민",
]

def classify_all(products):
    titles = [f"{i+1}. {p['title']}" for i, p in enumerate(products)]
    titles_str = "\n".join(titles)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": f"""제품명을 보고 아래 카테고리 중 하나로 분류하세요.

카테고리: {json.dumps(CATEGORIES, ensure_ascii=False)}

반드시 JSON 형식으로 응답하세요:
{{"results": [{{"index": 1, "category": "라면/면류"}}, ...]}}

모든 제품을 빠짐없이 분류하세요."""},
            {"role": "user", "content": f"다음 {len(products)}개 제품을 분류해주세요:\n\n{titles_str}"},
        ],
        response_format={"type": "json_object"},
        temperature=0,
        max_tokens=4000,
    )

    result = json.loads(response.choices[0].message.content)
    return {item["index"]: item["category"] for item in result["results"]}


def main():
    with open("output/classified_products.json", "r", encoding="utf-8") as f:
        products = json.load(f)

    print(f"총 {len(products)}개 제품 카테고리 분류 중...")

    # 한 번에 분류 (100개 정도는 충분히 가능)
    categories = classify_all(products)

    for i, p in enumerate(products):
        cat = categories.get(i + 1, "기타")
        p["category"] = cat

    with open("output/classified_products.json", "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

    # 통계
    cat_counts = {}
    for p in products:
        cat = p.get("category", "기타")
        cat_counts[cat] = cat_counts.get(cat, 0) + 1

    print("\n카테고리별 제품 수:")
    for cat, count in sorted(cat_counts.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}개")

    print(f"\n완료! output/classified_products.json 에 category 필드 추가됨")


if __name__ == "__main__":
    main()
