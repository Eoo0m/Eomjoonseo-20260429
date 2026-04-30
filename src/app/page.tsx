import products from "@/data/products.json";
import MainContent from "./MainContent";

type Product = {
  title: string;
  main_image: string;
  url: string;
  category?: string;
  price?: string;
  tags: Record<string, string[]>;
};

const TAGS = ["맛", "건강", "가성비", "다이어트", "조리 편의성", "가족/아이용", "재구매 의사"];

function selectTop20(products: Product[]): Product[] {
  const scored = products
    .filter((p) => p.main_image)
    .map((p) => {
      const tagCount = TAGS.filter(
        (t) => p.tags[t] && p.tags[t].length > 0
      ).length;
      return { product: p, score: tagCount };
    })
    .sort((a, b) => b.score - a.score);

  return scored.slice(0, 20).map((s) => s.product);
}

export default function Home() {
  const top20 = selectTop20(products as Product[]);

  return (
    <div className="min-h-screen bg-white">
      <header className="sticky top-0 z-50 bg-white/95 backdrop-blur-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 py-5">
          <h1 className="text-2xl font-bold tracking-[0.3em] text-red-600 text-center">
            REVIEWPICK
          </h1>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6">
        <MainContent defaultProducts={top20} tags={TAGS} />
      </main>
    </div>
  );
}
