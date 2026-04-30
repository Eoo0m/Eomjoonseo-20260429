"""
쿠팡 가격 크롤러 - 기존 products.json의 URL로 가격 수집

사용법:
1. Chrome 디버그 모드 실행:
   /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
     --remote-debugging-port=9222 --user-data-dir=/tmp/coupang_chrome

2. 스크립트 실행:
   python3 scrape_prices.py
"""

import asyncio
import random
import json
import os
from playwright.async_api import async_playwright

PRODUCTS_FILE = "output/products.json"


async def human_delay(min_sec=2, max_sec=5):
    await asyncio.sleep(random.uniform(min_sec, max_sec))


async def random_mouse_move(page):
    for _ in range(random.randint(1, 3)):
        await page.mouse.move(random.randint(100, 1200), random.randint(100, 700))
        await asyncio.sleep(random.uniform(0.1, 0.3))


async def connect_to_chrome():
    pw = await async_playwright().start()
    browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9222")
    context = browser.contexts[0]
    page = context.pages[0] if context.pages else await context.new_page()
    return pw, browser, context, page


async def scrape_price(page, url, idx, total):
    """제품 페이지에서 가격 추출"""
    await human_delay(3, 7)

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    except Exception as e:
        print(f"  [{idx+1}/{total}] 페이지 로드 실패: {e}")
        return None

    await human_delay(2, 4)
    await random_mouse_move(page)

    content = await page.content()
    if "Access Denied" in content:
        print(f"  [{idx+1}/{total}] Access Denied - 20초 대기 후 재시도...")
        await human_delay(15, 25)
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await human_delay(3, 5)
        except Exception:
            return None

    # 가격 추출 - 여러 셀렉터 시도
    price_selectors = [
        "div.sales-price-amount",
        "span.total-price strong",
        "div.prod-sale-price .total-price",
        "span.price-info",
        ".prod-price .total-price strong",
        "div.price-amount",
    ]

    for sel in price_selectors:
        elem = await page.query_selector(sel)
        if elem:
            text = (await elem.inner_text()).strip()
            # 숫자와 콤마만 추출
            price_str = "".join(c for c in text if c.isdigit() or c == ",")
            if price_str:
                print(f"  [{idx+1}/{total}] {price_str}원")
                return price_str

    # fallback: 페이지 전체에서 가격 패턴 찾기
    try:
        price_elements = await page.query_selector_all("[class*='price']")
        for elem in price_elements:
            text = (await elem.inner_text()).strip()
            if "원" in text and any(c.isdigit() for c in text):
                price_str = "".join(c for c in text.split("원")[0] if c.isdigit() or c == ",")
                if price_str and len(price_str) >= 3:
                    print(f"  [{idx+1}/{total}] {price_str}원 (fallback)")
                    return price_str
    except Exception:
        pass

    print(f"  [{idx+1}/{total}] 가격 찾지 못함")
    return None


async def main():
    if not os.path.exists(PRODUCTS_FILE):
        print(f"[오류] {PRODUCTS_FILE}이 없습니다.")
        return

    with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
        products = json.load(f)

    # 이미 가격이 있는 제품 건너뛰기
    remaining = [(i, p) for i, p in enumerate(products) if not p.get("price") and p.get("url")]
    total = len(products)
    print(f"총 {total}개 제품 중 {len(remaining)}개 가격 수집 필요")

    if not remaining:
        print("모든 제품에 가격이 이미 있습니다.")
        return

    try:
        pw, browser, context, page = await connect_to_chrome()
        print("[✓] Chrome 연결 성공!\n")
    except Exception as e:
        print(f"[✗] Chrome 연결 실패: {e}")
        print("\nChrome 디버그 모드를 먼저 실행하세요:")
        print('  /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome \\')
        print('    --remote-debugging-port=9222 --user-data-dir=/tmp/coupang_chrome')
        return

    try:
        for i, (orig_idx, product) in enumerate(remaining):
            price = await scrape_price(page, product["url"], i, len(remaining))
            if price:
                products[orig_idx]["price"] = price
            else:
                products[orig_idx]["price"] = ""

            # 5개마다 중간 저장
            if (i + 1) % 5 == 0 or i == len(remaining) - 1:
                with open(PRODUCTS_FILE, "w", encoding="utf-8") as f:
                    json.dump(products, f, ensure_ascii=False, indent=2)
                print(f"  [저장] {i+1}/{len(remaining)} 완료\n")

            await human_delay(5, 10)
    finally:
        await pw.stop()

    # 최종 저장
    with open(PRODUCTS_FILE, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

    # 통계
    with_price = sum(1 for p in products if p.get("price"))
    print(f"\n{'='*60}")
    print(f"완료! {with_price}/{total}개 제품 가격 수집")
    print(f"결과: {PRODUCTS_FILE}")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
