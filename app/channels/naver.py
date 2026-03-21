"""네이버 스마트스토어 주문 수집"""
import time
import base64
import requests
import bcrypt
from datetime import datetime, timedelta, timezone
from app.config import FETCH_DAYS

BASE_URL = "https://api.commerce.naver.com/external"
KST = timezone(timedelta(hours=9))


# ── 인증 ─────────────────────────────────────────

def _get_token(client_id: str, client_secret: str) -> str:
    timestamp = int(time.time() * 1000)
    password = f"{client_id}_{timestamp}"
    hashed = bcrypt.hashpw(password.encode("utf-8"), client_secret.encode("utf-8"))
    signature = base64.b64encode(hashed).decode("utf-8")

    resp = requests.post(
        f"{BASE_URL}/v1/oauth2/token",
        params={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "timestamp": timestamp,
            "client_secret_sign": signature,
            "type": "SELF",
        },
        headers={"content-type": "application/x-www-form-urlencoded"},
        timeout=10,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"[네이버] 토큰 발급 실패 (HTTP {resp.status_code}): {resp.text[:200]}")
    token = resp.json().get("access_token")
    if not token:
        raise RuntimeError(f"[네이버] 토큰 없음: {resp.json()}")
    return token


def _api_get(token: str, path: str, params: dict = None) -> dict:
    resp = requests.get(
        f"{BASE_URL}{path}",
        headers={"Authorization": f"Bearer {token}"},
        params=params,
        timeout=15,
    )
    if resp.status_code not in (200,):
        raise RuntimeError(f"API 오류 ({resp.status_code}): {resp.text[:300]}")
    return resp.json()


def _api_post(token: str, path: str, body: dict) -> dict:
    resp = requests.post(
        f"{BASE_URL}{path}",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=body,
        timeout=15,
    )
    if resp.status_code not in (200,):
        raise RuntimeError(f"API 오류 ({resp.status_code}): {resp.text[:300]}")
    return resp.json()


# ── 수집 ─────────────────────────────────────────

def _fmt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000+09:00")


def _get_order_ids(token: str, days: int = None) -> list[str]:
    now = datetime.now(KST)
    all_ids = []
    fetch_days = days or FETCH_DAYS

    for day_offset in range(fetch_days, 0, -1):
        day_start = now - timedelta(days=day_offset)
        day_end = day_start + timedelta(days=1)
        params = {
            "lastChangedFrom": _fmt(day_start),
            "lastChangedTo": _fmt(day_end),
            "limitCount": 300,
        }
        for attempt in range(2):
            try:
                data = _api_get(token, "/v1/pay-order/seller/product-orders/last-changed-statuses", params)
                inner = data.get("data") or data
                statuses = inner.get("lastChangeStatuses") if isinstance(inner, dict) else []
                if statuses:
                    all_ids.extend(s["productOrderId"] for s in statuses if s.get("productOrderId"))
                time.sleep(0.3)
                break
            except Exception as e:
                if "429" in str(e) and attempt == 0:
                    time.sleep(1.5)
                else:
                    print(f"  [WARNING] {day_start.date()} 조회 실패: {e}")
                    break

    return list(dict.fromkeys(all_ids))


def _get_details(token: str, ids: list[str]) -> list[dict]:
    orders = []
    for i in range(0, len(ids), 100):
        chunk = ids[i:i + 100]
        data = _api_post(token, "/v1/pay-order/seller/product-orders/query", {"productOrderIds": chunk})
        for row in data.get("data") or []:
            po = row.get("productOrder") or {}
            o  = row.get("order") or {}
            orders.append({
                "order_id":      o.get("orderId", ""),
                "product_name":  po.get("productName", ""),
                "quantity":      po.get("quantity", 0),
                "unit_price":    po.get("unitPrice", 0),
                "payment_amount": po.get("totalPaymentAmount", 0),
                "order_status":  po.get("productOrderStatus", ""),
                "order_date":    o.get("orderDate", ""),
            })
    return orders


def fetch(creds: dict, days: int = None) -> list[dict]:
    """외부 진입점: creds = {client_id, client_secret}, days=조회일수(None이면 FETCH_DAYS)"""
    print(f"  [네이버] 토큰 발급 중...")
    token = _get_token(creds["client_id"], creds["client_secret"])
    ids = _get_order_ids(token, days=days)
    print(f"  [네이버] 주문 ID {len(ids)}건 수집")
    if not ids:
        return []
    orders = _get_details(token, ids)
    print(f"  [네이버] 상세 파싱 완료 {len(orders)}건")
    return orders
