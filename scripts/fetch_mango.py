"""더망고 매출통계 수집 (Playwright 브라우저 자동화)"""
import sys
import os
import re
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
from app.db import init_db, save_orders

load_dotenv()

MANGO_SITES = []
for i in range(1, 10):
    url = os.getenv(f"MANGO{i}_URL")
    uid = os.getenv(f"MANGO{i}_ID")
    pwd = os.getenv(f"MANGO{i}_PW")
    if url and uid and pwd:
        MANGO_SITES.append({"name": f"mango{i}", "url": url, "id": uid, "pw": pwd})


def parse_amount(text: str) -> int:
    """'1,751,100\n(20건)' -> 1751100"""
    text = text.strip()
    if not text or text == "-":
        return 0
    # 숫자와 콤마만 추출 (첫 번째 줄)
    first_line = text.split("\n")[0].strip()
    digits = re.sub(r"[^\d]", "", first_line)
    return int(digits) if digits else 0


def fetch_monthly(page, year: int, month: int) -> list[dict]:
    """특정 월의 일별 합계 수집"""
    print(f"    {year}년 {month}월 조회 중...")

    # 년도 선택
    page.select_option('select[name="search_year"]', str(year))
    time.sleep(0.3)
    # 월 선택
    page.select_option('select[name="search_month"]', str(month))
    time.sleep(0.3)
    # 매출검색 버튼 클릭
    page.click('text=매출검색')
    time.sleep(3)

    # 수집사이트별 통계 테이블에서 합계 컬럼 수집
    # 두 번째 테이블(수집사이트별 통계)의 행들
    orders = []

    # 모든 테이블 찾기
    tables = page.query_selector_all("table")
    target_table = None

    for table in tables:
        header_text = table.inner_text()
        if "합계" in header_text and "AKmall" in header_text or "FashionPlus" in header_text:
            target_table = table
            break

    if not target_table:
        # 마켓별 통계 테이블도 시도
        for table in tables:
            header_text = table.inner_text()
            if "합계" in header_text and "일" in header_text:
                target_table = table
                break

    if not target_table:
        print(f"    테이블을 찾을 수 없습니다.")
        return []

    rows = target_table.query_selector_all("tr")
    if not rows:
        return []

    # 헤더에서 합계 컬럼 인덱스 찾기
    header_cells = rows[0].query_selector_all("td, th")
    total_idx = -1
    for idx, cell in enumerate(header_cells):
        if "합계" in cell.inner_text():
            total_idx = idx
            break

    if total_idx == -1:
        print(f"    합계 컬럼을 찾을 수 없습니다.")
        return []

    # 데이터 행 수집
    for row in rows[1:]:
        cells = row.query_selector_all("td")
        if len(cells) <= total_idx:
            continue

        day_text = cells[0].inner_text().strip()
        day_match = re.match(r"(\d+)일", day_text)
        if not day_match:
            continue

        day = int(day_match.group(1))
        total_text = cells[total_idx].inner_text()
        amount = parse_amount(total_text)

        if amount > 0:
            order_date = f"{year}-{month:02d}-{day:02d}"
            orders.append({
                "order_id": f"mango_{order_date}",
                "product_name": "더망고 일매출",
                "quantity": 1,
                "unit_price": amount,
                "payment_amount": amount,
                "order_status": "paid",
                "order_date": order_date,
            })

    print(f"    {len(orders)}일 수집, 합계 {sum(o['payment_amount'] for o in orders):,}원")
    return orders


def fetch_site(site: dict, months: list[tuple[int, int]]):
    """한 사이트에서 여러 월 수집"""
    print(f"\n▶ [{site['name']}] 수집 시작")
    print(f"  URL: {site['url']}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # 디버깅용 브라우저 표시
        context = browser.new_context()
        page = context.new_page()

        # 로그인
        print(f"  로그인 중...")
        page.goto(site["url"], wait_until="networkidle", timeout=30000)
        time.sleep(1)

        page.fill('input[name="user_id"], input[name="id"], #user_id, #id', site["id"])
        page.fill('input[name="user_passwd"], input[name="passwd"], input[name="password"], #passwd, #password', site["pw"])

        # 로그인 버튼 클릭
        login_btn = page.query_selector('input[type="submit"], button[type="submit"], .btn_login, input[value="로그인"]')
        if login_btn:
            login_btn.click()
        else:
            page.keyboard.press("Enter")
        time.sleep(3)

        # 매출통계 페이지로 이동
        # URL 패턴: /mall/admin/ 기반
        base_url = site["url"].replace("/admin_login.php", "")
        stats_url = f"{base_url}/admin_sales_stats.php"
        print(f"  매출통계 페이지 이동: {stats_url}")
        page.goto(stats_url, wait_until="networkidle", timeout=30000)
        time.sleep(2)

        # 월별 수집
        all_orders = []
        for year, month in months:
            orders = fetch_monthly(page, year, month)
            all_orders.extend(orders)
            time.sleep(1)

        browser.close()

    return all_orders


def run():
    init_db()

    if not MANGO_SITES:
        print("더망고 사이트 설정이 없습니다. .env 파일을 확인하세요.")
        return

    # 2026년 1~3월 수집
    months = [(2026, 1), (2026, 2), (2026, 3)]

    for site in MANGO_SITES:
        orders = fetch_site(site, months)
        if orders:
            saved = save_orders("themango", site["name"], orders)
            print(f"  [{site['name']}] 총 {len(orders)}건 수집, {saved}건 신규 저장")
        else:
            print(f"  [{site['name']}] 수집된 데이터 없음")

    print("\n=== 더망고 수집 완료 ===")


if __name__ == "__main__":
    run()
