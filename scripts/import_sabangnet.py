"""사방넷 엑셀 → DB 임포트 (네이버/쿠팡 제외)"""
import sys
import os
import re
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app.db import init_db, get_conn

# 제외할 쇼핑몰 (이미 API 연동됨)
EXCLUDE = {"스마트스토어", "Cafe24(신) 유튜브쇼핑"}

# 쇼핑몰명 → channel key 매핑
SHOP_KEY = {
    "쿠팡":                 "coupang",
    "CJ온스타일":           "cjonstyle",
    "Cafe24(신) 유튜브쇼핑": "cafe24_youtube",
    "ZVZO":                "zvzo",
    "신세계몰(신)":          "shinsegae",
    "GS shop":             "gsshop",
    "컬리":                 "kurly",
    "롯데온":               "lotteon",
    "카카오톡스토어":         "kakao",
    "우리의식탁":            "woorisiktuk",
    "토스쇼핑":              "toss",
    "웰스토리몰2.0(메인몰)":  "wellstory",
    "신세계TV쇼핑":          "shinsegaetv",
    "11번가":               "11st",
    "ESM지마켓":             "gmarket",
    "ESM옥션":              "auction",
}


def parse_month_from_filename(filename: str) -> str:
    """파일명에서 월 추출: '2026년01월.xlsx' → '2026-01'"""
    m = re.search(r"(\d{4})년\s*(\d{1,2})월", filename)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}"
    raise ValueError(f"파일명에서 월을 추출할 수 없습니다: {filename}")


def parse_excel(filepath: str) -> list[dict]:
    """사방넷 엑셀 파싱 → [{shop_name, channel, quantity, amount, month}]"""
    filename = os.path.basename(filepath)
    month = parse_month_from_filename(filename)

    df = pd.read_excel(filepath, header=None)

    results = []
    for idx in range(4, len(df)):  # 데이터는 row 4부터 (0-indexed: header0, header1, data...)
        row = df.iloc[idx]
        shop_name = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ""

        # 합계 행이나 빈 행 스킵
        if not shop_name or shop_name == "nan" or "합" in str(row.iloc[0]):
            continue

        # 제외 대상
        if shop_name in EXCLUDE:
            continue

        # 순매출 금액 (col 9)
        amount_raw = row.iloc[9]
        try:
            amount = int(float(str(amount_raw).replace(",", "")))
        except (ValueError, TypeError):
            continue

        # 순매출 수량 (col 8)
        qty_raw = row.iloc[8]
        try:
            quantity = int(float(str(qty_raw).replace(",", "")))
        except (ValueError, TypeError):
            quantity = 0

        channel = SHOP_KEY.get(shop_name, shop_name.lower().replace(" ", "_"))

        results.append({
            "shop_name": shop_name,
            "channel": channel,
            "quantity": quantity,
            "amount": amount,
            "month": month,
        })

    return results


def import_to_db(project: str, data: list[dict]):
    """월별 집계 데이터를 orders 테이블에 저장"""
    from datetime import datetime
    saved_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    rows = []
    for d in data:
        # order_id: 월별 집계이므로 "sabangnet_{channel}_{month}" 형태
        order_id = f"sabangnet_{d['channel']}_{d['month']}"
        order_date = f"{d['month']}-01T00:00:00+09:00"  # 월 첫째날

        rows.append((
            project,
            d["channel"],
            order_id,
            d["shop_name"],
            d["quantity"],
            0,  # unit_price
            d["amount"],
            "confirmed",
            order_date,
            saved_at,
        ))

    with get_conn() as conn:
        # 기존 사방넷 데이터 삭제 후 재삽입 (중복 방지)
        for d in data:
            order_id = f"sabangnet_{d['channel']}_{d['month']}"
            conn.execute(
                "DELETE FROM orders WHERE project=? AND order_id=?",
                (project, order_id)
            )

        cursor = conn.executemany("""
            INSERT OR REPLACE INTO orders
            (project, channel, order_id, product_name, quantity, unit_price,
             payment_amount, order_status, order_date, saved_at)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, rows)

    return len(rows)


def run():
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sabangnet_data")
    if not os.path.exists(data_dir):
        print(f"[오류] {data_dir} 폴더가 없습니다.")
        return

    init_db()

    files = [f for f in os.listdir(data_dir) if f.endswith(".xlsx")]
    if not files:
        print("[오류] xlsx 파일이 없습니다.")
        return

    total_imported = 0
    all_data = []

    for f in sorted(files):
        filepath = os.path.join(data_dir, f)
        print(f"\n  [{f}] 파싱 중...")
        data = parse_excel(filepath)
        all_data.extend(data)

        for d in data:
            print(f"    {d['shop_name']:20s}  수량: {d['quantity']:>5}  매출: ₩{d['amount']:>12,}")

    if all_data:
        saved = import_to_db("glener", all_data)
        total_imported = saved
        print(f"\n  [완료] {total_imported}건 저장")

    # 결과 확인
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT channel, COUNT(*), COALESCE(SUM(payment_amount),0)
            FROM orders WHERE project='glener'
            GROUP BY channel ORDER BY 3 DESC
        """).fetchall()
        print(f"\n=== 글리너 채널별 현황 ===")
        for r in rows:
            print(f"  {r[0]:20s}  {r[1]:>5}건  ₩{r[2]:>12,}")


if __name__ == "__main__":
    run()
