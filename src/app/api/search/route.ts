import { NextRequest, NextResponse } from "next/server";
import OpenAI from "openai";
import products from "@/data/products.json";

const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

const FOOD_CATEGORIES = [
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
];

const REVIEW_TAGS = [
  "맛",
  "건강",
  "가성비",
  "다이어트",
  "조리 편의성",
  "가족/아이용",
  "재구매 의사",
];

type Product = {
  title: string;
  main_image: string;
  url: string;
  category?: string;
  tags: Record<string, string[]>;
};

export async function POST(request: NextRequest) {
  try {
    const { query } = await request.json();

    if (!query || typeof query !== "string") {
      return NextResponse.json(
        { error: "query is required" },
        { status: 400 }
      );
    }

    // GPT로 사용자 의도 분석 → 음식 카테고리 + 리뷰 태그 추출
    const response = await openai.chat.completions.create({
      model: "gpt-4o-mini",
      messages: [
        {
          role: "system",
          content: `사용자의 검색 쿼리를 분석하여 두 가지를 추출하세요:

1. food_categories: 사용자가 원하는 음식 카테고리 (복수 가능)
   선택지: ${JSON.stringify(FOOD_CATEGORIES)}

2. review_tags: 사용자가 관심있는 리뷰 관점 (복수 가능)
   선택지: ${JSON.stringify(REVIEW_TAGS)}

규칙:
- 사용자 쿼리에서 음식 종류 관련 키워드 → food_categories로 매핑
- 사용자 쿼리에서 리뷰 관점 키워드 → review_tags로 매핑
- "맛있는" → review_tags에 "맛" 추가
- "저렴한", "싼" → review_tags에 "가성비" 추가
- "간편한", "쉬운", "빠른" → review_tags에 "조리 편의성" 추가
- "건강한", "영양" → review_tags에 "건강" 추가
- "아이", "아기", "가족" → review_tags에 "가족/아이용" 추가
- "다이어트", "살", "체중" → review_tags에 "다이어트" 추가
- "또 사고 싶은", "추천" → review_tags에 "재구매 의사" 추가
- 카테고리가 불분명하면 관련 있는 것 모두 포함
- 리뷰 태그가 불분명하면 "맛"을 기본값으로

반드시 JSON으로만 응답:
{"food_categories": [...], "review_tags": [...]}`,
        },
        { role: "user", content: query },
      ],
      response_format: { type: "json_object" },
      temperature: 0.3,
      max_tokens: 200,
    });

    const parsed = JSON.parse(response.choices[0].message.content || "{}");
    const foodCategories: string[] = parsed.food_categories || [];
    const reviewTags: string[] = parsed.review_tags || ["맛"];

    // 1. 음식 카테고리로 제품 필터링
    let filtered: Product[] = products as Product[];
    if (foodCategories.length > 0) {
      filtered = filtered.filter(
        (p) => p.category && foodCategories.includes(p.category)
      );
    }

    // 카테고리 매칭 결과가 없으면 전체에서 제목 키워드 매칭
    if (filtered.length === 0) {
      const keywords = query
        .split(/\s+/)
        .filter((w: string) => w.length >= 2);
      filtered = (products as Product[]).filter((p) =>
        keywords.some((kw: string) => p.title.includes(kw))
      );
    }

    // 그래도 없으면 전체 반환
    if (filtered.length === 0) {
      filtered = products as Product[];
    }

    // 2. 리뷰 태그에 맞는 리뷰가 있는 제품 우선 정렬
    const scored = filtered
      .filter((p) => p.main_image)
      .map((p) => {
        let score = 0;
        const highlightReviews: Record<string, string[]> = {};
        for (const tag of reviewTags) {
          if (p.tags[tag] && p.tags[tag].length > 0) {
            score += p.tags[tag].length;
            highlightReviews[tag] = p.tags[tag].slice(0, 2);
          }
        }
        return { ...p, score, highlightReviews };
      })
      .sort((a, b) => b.score - a.score)
      .slice(0, 20);

    return NextResponse.json({
      query,
      food_categories: foodCategories,
      review_tags: reviewTags,
      products: scored,
    });
  } catch (error) {
    console.error("Search API error:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
