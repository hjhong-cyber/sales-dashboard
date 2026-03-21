"""변경 주문 조회 → 주문 상세 조회 (일별 청크로 300건 제한 우회)"""
import time
from datetime import datetime, timedelta, timezone
from app.client import api_get, api_post
from app.config import FETCH_DAYS

KST = timezone(timedelta(hours=9))


def _fmt(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000+09:00")


def get_changed_order_ids(token: str) -> list[str]:
    """
    일별 청크로 나눠서 변경 주문 ID 수집
    → 하루씩 쪼개면 하루 300건 넘어도 누락 최소화
    """
    now = datetime.now(KST)
    all_ids = []

    for day_offset in range(FETCH_DAYS, 0, -1):
        day_start = now - timedelta(days=day_offset)
        day_end = day_start + timedelta(days=1)

        params = {
            "lastChangedFrom": _fmt(day_start),
            "lastChangedTo": _fmt(day_end),
            "limitCount": 300,
        }
        try:
            data = api_get(token, "/v1/pay-order/seller/product-orders/last-changed-statuses", params)
            inner = data.get("data") or data
            statuses = inner.get("lastChangeStatuses") if isinstance(inner, dict) else []
            if statuses:
                ids = [s.get("productOrderId") for s in statuses if s.get("productOrderId")]
                all_ids.extend(ids)
            time.sleep(0.3)
        except Exception as e:
            if "429" in str(e):
                print(f"[RATE_LIMIT] {day_start.date()} - 1초 대기 후 재시도")
                time.sleep(1.5)
                try:
                    data = api_get(token, "/v1/pay-order/seller/product-orders/last-changed-statuses", params)
                    inner = data.get("data") or data
                    statuses = inner.get("lastChangeStatuses") if isinstance(inner, dict) else []
                    if statuses:
                        ids = [s.get("productOrderId") for s in statuses if s.get("productOrderId")]
                        all_ids.extend(ids)
                except Exception as e2:
                    print(f"[WARNING] {day_start.date()} 재시도 실패: {e2}")
            else:
                print(f"[WARNING] {day_start.date()} 조회 실패: {e}")

    # 중복 제거
    unique_ids = list(dict.fromkeys(all_ids))
    print(f"[OK] 변경 주문 ID 수신: {len(unique_ids)}건 (기간 {FETCH_DAYS}일)")
    return unique_ids


def get_order_details(token: str, product_order_ids: list[str]) -> list[dict]:
    """
    주문 상세 조회 (100건씩 청크)
    API: POST /v1/pay-order/seller/product-orders/query
    """
    if not product_order_ids:
        return []

    orders = []
    chunk_size = 100
    for i in range(0, len(product_order_ids), chunk_size):
        chunk = product_order_ids[i:i + chunk_size]
        body = {"productOrderIds": chunk}
        data = api_post(token, "/v1/pay-order/seller/product-orders/query", body)

        rows = data.get("data") or []
        for row in rows:
            po = row.get("productOrder") or {}
            o = row.get("order") or {}
            orders.append({
                "product_order_id": po.get("productOrderId", ""),
                "order_id": o.get("orderId", ""),
                "product_name": po.get("productName", "상품명 없음"),
                "quantity": po.get("quantity", 0),
                "unit_price": po.get("unitPrice", 0),
                "payment_amount": po.get("totalPaymentAmount", 0),
                "order_status": po.get("productOrderStatus", ""),
                "order_date": o.get("orderDate", ""),
            })

    print(f"[OK] 주문 상세 파싱 완료: {len(orders)}건")
    return orders


def fetch_all(token: str) -> list[dict]:
    ids = get_changed_order_ids(token)
    if not ids:
        print("[WARNING] 수집된 주문이 없습니다.")
        return []
    return get_order_details(token, ids)
