"""
쿠팡 스크래퍼 - Chrome 디버그 모드 연결 방식

사용법:
1. Chrome 디버그 모드 실행:
   /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
     --remote-debugging-port=9222 --user-data-dir=/tmp/coupang_chrome

2. Chrome에서 쿠팡 접속 확인

3. 스크립트 실행:
   python3 coupang_scraper.py collect   # 1단계: 제품 URL 수집
   python3 coupang_scraper.py scrape    # 2단계: 제품 상세 스크래핑 (이어하기 지원)
"""

import asyncio
import random
import json
import os
import re
import sys
import requests
from urllib.parse import urljoin
from playwright.async_api import async_playwright

# 설정
CATEGORY_URL = "https://www.coupang.com/np/categories/194276"
OUTPUT_DIR = "output"
IMAGE_DIR = os.path.join(OUTPUT_DIR, "images")
URLS_FILE = os.path.join(OUTPUT_DIR, "product_urls.json")
PRODUCTS_FILE = os.path.join(OUTPUT_DIR, "products.json")
REVIEW_COUNT = 100
MIN_PRODUCTS = 120

os.makedirs(IMAGE_DIR, exist_ok=True)


# ──────────────────────────────────────
# 유틸리티
# ──────────────────────────────────────

async def human_delay(min_sec=3, max_sec=7):
    await asyncio.sleep(random.uniform(min_sec, max_sec))


async def random_mouse_move(page):
    for _ in range(random.randint(2, 4)):
        await page.mouse.move(random.randint(100, 1200), random.randint(100, 700))
        await asyncio.sleep(random.uniform(0.1, 0.4))


def download_image(url, filepath):
    try:
        if url.startswith("//"):
            url = "https:" + url
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
            "Referer": "https://www.coupang.com/",
        }
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            with open(filepath, "wb") as f:
                f.write(resp.content)
            return True
    except Exception as e:
        print(f"  [오류] 이미지 다운로드 실패: {e}")
    return False


async def connect_to_chrome():
    pw = await async_playwright().start()
    browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9222")
    context = browser.contexts[0]
    page = context.pages[0] if context.pages else await context.new_page()
    return pw, browser, context, page


# ──────────────────────────────────────
# 1단계: 제품 URL 수집
# ──────────────────────────────────────

async def collect_from_single_page(page, urls_set):
    await random_mouse_move(page)
    for _ in range(5):
        await page.evaluate(f"window.scrollBy(0, {random.randint(600, 1200)})")
        await human_delay(1.5, 3)

    new_urls = []
    for selector in [
        "li[class*='ProductUnit'] a[href*='/vp/products/']",
        "li[class*='productUnit'] a[href*='/vp/products/']",
        "a[href*='/vp/products/']",
    ]:
        elements = await page.query_selector_all(selector)
        if elements:
            for elem in elements:
                href = await elem.get_attribute("href")
                if href and "/vp/products/" in href:
                    full_url = urljoin("https://www.coupang.com", href)
                    if full_url not in urls_set:
                        urls_set.add(full_url)
                        new_urls.append(full_url)
            break
    return new_urls


async def cmd_collect(page):
    """제품 URL 수집 후 파일 저장"""
    all_urls = []
    urls_set = set()

    # 기존 URL 파일 있으면 로드
    if os.path.exists(URLS_FILE):
        with open(URLS_FILE, "r", encoding="utf-8") as f:
            all_urls = json.load(f)
        urls_set = set(all_urls)
        print(f"[기존] {len(all_urls)}개 URL 로드됨")

    page_num = 1
    while len(all_urls) < MIN_PRODUCTS:
        page_url = f"{CATEGORY_URL}?page={page_num}"
        print(f"\n[페이지 {page_num}] 이동 중... (현재 {len(all_urls)}개)")
        await page.goto(page_url, wait_until="domcontentloaded", timeout=30000)
        await human_delay(3, 5)

        content = await page.content()
        if "Access Denied" in content:
            print(f"[!] 차단됨. Chrome에서 직접 열어주세요: {page_url}")
            input(">>> 정상 로드 후 Enter... ")

        new_urls = await collect_from_single_page(page, urls_set)
        all_urls.extend(new_urls)
        print(f"[페이지 {page_num}] +{len(new_urls)}개 (총 {len(all_urls)}개)")

        # 수집할 때마다 저장
        with open(URLS_FILE, "w", encoding="utf-8") as f:
            json.dump(all_urls, f, ensure_ascii=False, indent=2)

        if len(new_urls) == 0:
            print("[!] 더 이상 제품이 없습니다.")
            break

        page_num += 1
        await human_delay(3, 6)

    print(f"\n[완료] 총 {len(all_urls)}개 제품 URL 저장: {URLS_FILE}")


# ──────────────────────────────────────
# 2단계: 제품 상세 스크래핑
# ──────────────────────────────────────

async def scrape_product(page, product_url, index):
    print(f"\n[{index+1}] 스크래핑 중...")
    await human_delay(5, 10)

    await page.goto(product_url, wait_until="domcontentloaded", timeout=30000)
    await human_delay(3, 5)
    await random_mouse_move(page)

    content = await page.content()
    if "Access Denied" in content:
        print("  [!] Access Denied - 20초 대기 후 재시도...")
        await human_delay(15, 25)
        await page.goto(product_url, wait_until="domcontentloaded", timeout=30000)
        await human_delay(3, 5)

    result = {"url": product_url}

    # 1. 제품명
    for sel in [
        "h1.product-title span.twc-font-bold",
        "h1.product-title span",
        "h1.product-title",
        "h2.prod-buy-header__title",
        ".prod-buy-header h1",
    ]:
        elem = await page.query_selector(sel)
        if elem:
            result["title"] = (await elem.inner_text()).strip()
            break
    if not result.get("title"):
        result["title"] = ""
    print(f"  제품명: {result['title']}")

    # 2. 대표 이미지
    result["main_image"] = ""
    for sel in [
        'img[alt="Product image"]',
        "img.prod-image__detail",
        ".prod-image img",
        ".twc-relative img[src*='coupangcdn']",
    ]:
        elem = await page.query_selector(sel)
        if elem:
            img_url = await elem.get_attribute("src")
            if img_url:
                safe_name = re.sub(r'[^\w가-힣]', '_', result.get("title", f"product_{index}"))[:50]
                img_path = os.path.join(IMAGE_DIR, f"{index+1}_{safe_name}.jpg")
                if download_image(img_url, img_path):
                    result["main_image"] = img_path
                    print(f"  이미지 저장: {img_path}")
                else:
                    result["main_image"] = img_url
                break

    # 3. 상세 설명 이미지
    detail_images = []
    try:
        detail_tab = await page.query_selector("div[data-value='detail']")
        if detail_tab:
            await detail_tab.scroll_into_view_if_needed()
            await human_delay(2, 4)
        else:
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
            await human_delay(2, 4)

        for _ in range(5):
            await page.evaluate(f"window.scrollBy(0, {random.randint(500, 900)})")
            await human_delay(1, 2.5)

        detail_img_elems = await page.query_selector_all(
            ".product-detail-content img, .vendor-item img, .subType-IMAGE img"
        )
        detail_dir = os.path.join(IMAGE_DIR, f"detail_{index+1}")
        os.makedirs(detail_dir, exist_ok=True)

        for i, img in enumerate(detail_img_elems):
            src = await img.get_attribute("src") or await img.get_attribute("data-src") or ""
            if "coupangcdn" in src or "thumbnail" in src:
                img_path = os.path.join(detail_dir, f"detail_{i+1}.jpg")
                if download_image(src, img_path):
                    detail_images.append(img_path)
        print(f"  상세 이미지 {len(detail_images)}개 수집")
    except Exception as e:
        print(f"  [오류] 상세 설명 수집 실패: {e}")
    result["detail_images"] = detail_images

    # 4. 리뷰 수집 (페이지네이션으로 최대 REVIEW_COUNT개)
    reviews = []
    try:
        review_tab = await page.query_selector("div[data-value='review']")
        if review_tab:
            await review_tab.scroll_into_view_if_needed()
            await human_delay(1, 2)
            await page.evaluate("el => el.click()", review_tab)
            await human_delay(4, 6)

        review_page = 1
        while len(reviews) < REVIEW_COUNT:
            # 스크롤로 리뷰 로딩
            for _ in range(6):
                await page.evaluate("window.scrollBy(0, 500)")
                await human_delay(0.8, 1.5)

            # 리뷰 article 찾기
            review_articles = []
            for attempt in range(5):
                review_articles = await page.query_selector_all("article.twc-pt-\\[16px\\]")
                if review_articles:
                    break
                await page.evaluate("window.scrollBy(0, 500)")
                await human_delay(1, 2)

            if not review_articles:
                review_articles = await page.query_selector_all("article[class*='twc-border-b']")
            if not review_articles:
                review_articles = await page.query_selector_all("article.sdp-review__article__list")
            if not review_articles:
                print(f"  [리뷰 p{review_page}] 리뷰 없음, 중단")
                break

            # 현재 페이지 리뷰 추출
            count = 0
            for review_el in review_articles:
                review_data = {}

                try:
                    title_el = await review_el.query_selector("div.twc-font-bold.twc-text-bluegray-900")
                    if title_el:
                        review_data["title"] = (await title_el.inner_text()).strip()
                except Exception:
                    pass

                text_el = await review_el.query_selector('span[translate="no"]')
                if text_el:
                    review_data["text"] = (await text_el.inner_text()).strip()
                else:
                    text_el = await review_el.query_selector("div[class*='twc-break-all']")
                    if text_el:
                        review_data["text"] = (await text_el.inner_text()).strip()

                if not review_data.get("text"):
                    full_text = (await review_el.inner_text()).strip()
                    if full_text:
                        review_data["text"] = full_text[:500]

                if review_data.get("text"):
                    reviews.append(review_data)
                    count += 1

            print(f"  [리뷰 p{review_page}] +{count}개 (총 {len(reviews)}개)")

            if len(reviews) >= REVIEW_COUNT:
                break

            # 다음 페이지 버튼
            next_clicked = False
            review_section = await page.query_selector("#sdpReview, .sdp-review, .product-review")
            if review_section:
                next_page_num = review_page + 1
                buttons = await review_section.query_selector_all("button")
                for btn in buttons:
                    btn_text = (await btn.inner_text()).strip()
                    if btn_text == str(next_page_num):
                        await btn.scroll_into_view_if_needed()
                        await human_delay(0.5, 1)
                        await page.evaluate("el => el.click()", btn)
                        next_clicked = True
                        break
                if not next_clicked:
                    for btn in buttons:
                        btn_text = (await btn.inner_text()).strip()
                        aria = await btn.get_attribute("aria-label") or ""
                        if btn_text in [">", "›", "다음"] or "next" in aria.lower():
                            await btn.scroll_into_view_if_needed()
                            await human_delay(0.5, 1)
                            await page.evaluate("el => el.click()", btn)
                            next_clicked = True
                            break

            if not next_clicked:
                print(f"  [리뷰] 다음 페이지 없음, 중단")
                break

            review_page += 1
            await human_delay(3, 5)

        print(f"  리뷰 총 {len(reviews)}개 수집")
    except Exception as e:
        print(f"  [오류] 리뷰 수집 실패: {e}")
    result["reviews"] = reviews

    return result


async def cmd_scrape(page):
    """저장된 URL 목록 기반으로 제품 상세 스크래핑 (이어하기 지원)"""
    if not os.path.exists(URLS_FILE):
        print(f"[오류] URL 파일이 없습니다. 먼저 'collect'를 실행하세요.")
        return

    with open(URLS_FILE, "r", encoding="utf-8") as f:
        all_urls = json.load(f)
    print(f"[로드] {len(all_urls)}개 제품 URL")

    # 기존 결과 로드
    all_results = []
    done_urls = set()
    if os.path.exists(PRODUCTS_FILE):
        with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
            all_results = json.load(f)
        done_urls = {r["url"] for r in all_results}
        print(f"[이어하기] {len(all_results)}개 완료, {len(all_urls) - len(done_urls)}개 남음")

    remaining = [url for url in all_urls if url not in done_urls]

    for i, url in enumerate(remaining):
        idx = len(all_results)
        try:
            result = await scrape_product(page, url, idx)
            all_results.append(result)

            # 매번 중간 저장
            with open(PRODUCTS_FILE, "w", encoding="utf-8") as f:
                json.dump(all_results, f, ensure_ascii=False, indent=2)

            await human_delay(8, 15)
        except Exception as e:
            print(f"  [오류] 스크래핑 실패: {e}")
            continue

    print(f"\n{'=' * 60}")
    print(f"완료! 총 {len(all_results)}개 제품 수집")
    print(f"결과: {PRODUCTS_FILE}")
    print(f"{'=' * 60}")


# ──────────────────────────────────────
# 메인
# ──────────────────────────────────────

async def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""

    if cmd not in ("collect", "scrape"):
        print("사용법:")
        print("  python3 coupang_scraper.py collect   # 1단계: 제품 URL 수집")
        print("  python3 coupang_scraper.py scrape    # 2단계: 상세 스크래핑 (이어하기)")
        return

    print("=" * 60)
    print(f"쿠팡 스크래퍼 - {cmd}")
    print("=" * 60)

    try:
        pw, browser, context, page = await connect_to_chrome()
        print("[✓] Chrome 연결 성공!")
    except Exception as e:
        print(f"[✗] Chrome 연결 실패: {e}")
        print()
        print("Chrome 디버그 모드를 먼저 실행하세요:")
        print('  /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome \\')
        print('    --remote-debugging-port=9222 --user-data-dir=/tmp/coupang_chrome')
        return

    try:
        if cmd == "collect":
            await cmd_collect(page)
        elif cmd == "scrape":
            await cmd_scrape(page)
    finally:
        await pw.stop()


if __name__ == "__main__":
    asyncio.run(main())
