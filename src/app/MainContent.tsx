"use client";

import { useState } from "react";
import Image from "next/image";

type Product = {
  title: string;
  main_image: string;
  url: string;
  category?: string;
  tags: Record<string, string[]>;
  highlightReviews?: Record<string, string[]>;
};

type Props = {
  defaultProducts: Product[];
  tags: string[];
};

export default function MainContent({ defaultProducts, tags }: Props) {
  const [selectedTag, setSelectedTag] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [products, setProducts] = useState<Product[]>(defaultProducts);
  const [searchInfo, setSearchInfo] = useState<{
    food_categories: string[];
    review_tags: string[];
  } | null>(null);
  const [isSearchMode, setIsSearchMode] = useState(false);

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;

    setIsSearching(true);
    setSearchInfo(null);

    try {
      const res = await fetch("/api/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: searchQuery }),
      });

      if (!res.ok) throw new Error("Search failed");

      const data = await res.json();
      setProducts(data.products);
      setSearchInfo({
        food_categories: data.food_categories,
        review_tags: data.review_tags,
      });
      setIsSearchMode(true);

      // 첫 번째 리뷰 태그를 자동 선택
      if (data.review_tags.length > 0) {
        setSelectedTag(data.review_tags[0]);
      }
    } catch (err) {
      console.error("Search error:", err);
    } finally {
      setIsSearching(false);
    }
  };

  const handleReset = () => {
    setProducts(defaultProducts);
    setSearchInfo(null);
    setSearchQuery("");
    setSelectedTag(null);
    setIsSearchMode(false);
  };

  const handleTagClick = (tag: string) => {
    setSelectedTag((prev) => (prev === tag ? null : tag));
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleSearch();
  };

  return (
    <>
      {/* Search Bar */}
      <div className="mb-6">
        <div className="flex gap-2 max-w-2xl mx-auto">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="예: 가성비 좋은 간편식, 아이 간식 추천, 다이어트 음료..."
            className="flex-1 px-4 py-3 rounded-xl bg-white/10 border border-white/20 text-white placeholder-white/40 focus:outline-none focus:border-white/50 text-sm"
          />
          <button
            onClick={handleSearch}
            disabled={isSearching}
            className="px-6 py-3 rounded-xl bg-white text-black font-medium text-sm hover:bg-white/90 transition-colors disabled:opacity-50 cursor-pointer"
          >
            {isSearching ? "..." : "검색"}
          </button>
          {isSearchMode && (
            <button
              onClick={handleReset}
              className="px-4 py-3 rounded-xl bg-white/10 text-white/70 text-sm hover:bg-white/20 transition-colors cursor-pointer"
            >
              초기화
            </button>
          )}
        </div>

        {/* Search Result Info */}
        {searchInfo && (
          <div className="flex flex-wrap gap-2 justify-center mt-3 animate-fade-in">
            {searchInfo.food_categories.map((cat) => (
              <span
                key={cat}
                className="px-3 py-1 rounded-full bg-blue-500/20 text-blue-300 text-xs"
              >
                {cat}
              </span>
            ))}
            {searchInfo.review_tags.map((tag) => (
              <span
                key={tag}
                className="px-3 py-1 rounded-full bg-yellow-500/20 text-yellow-300 text-xs"
              >
                {tag}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Tag Bar */}
      <div className="sticky top-[73px] z-40 bg-black/95 backdrop-blur-sm py-4 -mx-4 px-4 border-b border-white/5">
        <div className="flex flex-wrap gap-2 justify-center">
          {tags.map((tag) => (
            <button
              key={tag}
              onClick={() => handleTagClick(tag)}
              className={`px-4 py-2 rounded-full text-sm font-medium transition-all duration-200 cursor-pointer ${
                selectedTag === tag
                  ? "bg-white text-black"
                  : "bg-white/10 text-white/80 hover:bg-white/20"
              }`}
            >
              {tag}
            </button>
          ))}
        </div>
      </div>

      {/* Product Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 mt-6">
        {products.map((product, idx) => {
          // 검색 모드에서는 highlightReviews 우선 사용
          const highlightReview =
            selectedTag && product.highlightReviews?.[selectedTag]?.[0];
          const tagReview =
            selectedTag && product.tags[selectedTag]?.[0];
          const reviewLine = highlightReview || tagReview || null;
          const hasTag =
            selectedTag &&
            (product.highlightReviews?.[selectedTag]?.length ||
              product.tags[selectedTag]?.length);
          const dimmed = selectedTag && !hasTag;

          return (
            <div
              key={idx}
              className={`group rounded-xl overflow-hidden transition-all duration-300 ${
                dimmed ? "opacity-30" : "opacity-100"
              }`}
            >
              <div className="relative aspect-square bg-white/5 overflow-hidden rounded-xl">
                {product.main_image && (
                  <Image
                    src={product.main_image}
                    alt={product.title}
                    fill
                    sizes="(max-width: 768px) 50vw, (max-width: 1024px) 33vw, 25vw"
                    className="object-contain p-2 group-hover:scale-105 transition-transform duration-300"
                  />
                )}
                {/* Category Badge */}
                {product.category && (
                  <span className="absolute top-2 left-2 px-2 py-0.5 rounded bg-white/15 text-white/70 text-[10px] backdrop-blur-sm">
                    {product.category}
                  </span>
                )}
              </div>

              <div className="pt-3 pb-2 px-1">
                <h3 className="text-sm text-white/90 font-medium line-clamp-2 leading-snug">
                  {product.title}
                </h3>

                {reviewLine && (
                  <p className="mt-2 text-xs leading-relaxed animate-fade-in">
                    <span className="bg-yellow-400/20 text-yellow-300 px-1.5 py-0.5 rounded">
                      {reviewLine}
                    </span>
                  </p>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {products.length === 0 && (
        <div className="text-center text-white/40 py-20">
          검색 결과가 없습니다.
        </div>
      )}
    </>
  );
}
