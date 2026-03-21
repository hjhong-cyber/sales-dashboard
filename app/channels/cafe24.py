"""Cafe24 주문 수집 (OAuth 2.0 + REST API)"""
import json
import os
import time
import webbrowser
import requests
from datetime import datetime, timedelta
from urllib.parse import urlencode
from app.config import FETCH_DAYS

TOKEN_DIR = ".cafe24_tokens"


def _token_path(project: str) -> str:
    os.makedirs(TOKEN_DIR, exist_ok=True)
    return os.path.join(TOKEN_DIR, f"{project}.json")


def _save_token(project: str, token_data: dict):
    with open(_token_path(project), "w") as f:
        json.dump(token_data, f)


def _load_token(project: str) -> dict | None:
    path = _token_path(project)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


def _refresh_token(project: str, creds: dict, token_data: dict) -> dict:
    """refresh_token으로 access_token 갱신"""
    mall_id       = creds["mall_id"]
    client_id     = creds["client_id"]
    client_secret = creds["client_secret"]

    resp = requests.post(
        f"https://{mall_id}.cafe24api.com/api/v2/oauth/token",
        auth=(client_id, client_secret),
        data={
            "grant_type": "refresh_token",
            "refresh_token": token_data["refresh_token"],
        },
        timeout=10,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"[Cafe24] 토큰 갱신 실패: {resp.text}")
    new_data = resp.json()
    _save_token(project, new_data)
    return new_data


def _authorize(project: str, creds: dict) -> dict:
    """브라우저 OAuth 인증 흐름 (최초 1회) - 수동 코드 입력 방식"""
    mall_id       = creds["mall_id"]
    client_id     = creds["client_id"]
    client_secret = creds["client_secret"]
    redirect_uri  = f"https://{mall_id}.cafe24.com/order/basket.html"

    auth_url = (
        f"https://{mall_id}.cafe24api.com/api/v2/oauth/authorize?"
        + urlencode({
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": "mall.read_application,mall.write_application,mall.read_product,mall.read_order",
            "state": project,
        })
    )

    print(f"\n  ┌─────────────────────────────────────────────┐")
    print(f"  │  [Cafe24] 아래 URL을 브라우저에서 열어주세요  │")
    print(f"  └─────────────────────────────────────────────┘")
    print(f"\n  {auth_url}\n")
    webbrowser.open(auth_url)

    print("  승인 후 브라우저 주소창의 URL에서 'code=...' 값을 복사해주세요.")
    print("  예: https://undefi88.cafe24.com/order/basket.html?code=XXXXXX&...")
    raw = input("\n  code 값 붙여넣기 (URL 전체 또는 code 값만): ").strip()

    # URL 전체를 붙여넣은 경우 code= 파라미터 추출
    if "code=" in raw:
        from urllib.parse import urlparse, parse_qs
        qs = parse_qs(urlparse(raw).query)
        code = qs.get("code", [None])[0]
    else:
        code = raw

    if not code:
        raise RuntimeError("[Cafe24] 코드가 입력되지 않았습니다.")

    resp = requests.post(
        f"https://{mall_id}.cafe24api.com/api/v2/oauth/token",
        auth=(client_id, client_secret),
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
        },
        timeout=10,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"[Cafe24] 토큰 교환 실패: {resp.text}")

    token_data = resp.json()
    _save_token(project, token_data)
    print("  [Cafe24] 인증 완료 및 토큰 저장")
    return token_data


def _get_access_token(project: str, creds: dict) -> str:
    """저장된 토큰 로드 → 만료 시 갱신 → 없으면 신규 인증"""
    token_data = _load_token(project)

    if token_data:
        expires_at = token_data.get("expires_at", 0)
        if time.time() < expires_at - 60:
            return token_data["access_token"]
        # refresh
        try:
            token_data = _refresh_token(project, creds, token_data)
            token_data["expires_at"] = time.time() + token_data.get("expires_in", 7200)
            _save_token(project, token_data)
            return token_data["access_token"]
        except Exception as e:
            print(f"  [Cafe24] 토큰 갱신 실패, 재인증 필요: {e}")

    # 최초 인증
    token_data = _authorize(project, creds)
    token_data["expires_at"] = time.time() + token_data.get("expires_in", 7200)
    _save_token(project, token_data)
    return token_data["access_token"]


def _fetch_orders(mall_id: str, access_token: str, days: int = None) -> list[dict]:
    """Cafe24 주문 목록 조회 (날짜 범위, 페이징) - 최대 6개월"""
    end_date   = datetime.now()
    fetch_days = days or FETCH_DAYS
    cafe24_max_days = min(fetch_days, 85)  # Cafe24는 최대 3개월 미만
    start_date = end_date - timedelta(days=cafe24_max_days)

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    orders = []
    offset = 0
    limit  = 100

    while True:
        params = {
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date":   end_date.strftime("%Y-%m-%d"),
            "limit":      limit,
            "offset":     offset,
        }
        resp = requests.get(
            f"https://{mall_id}.cafe24api.com/api/v2/admin/orders",
            headers=headers,
            params=params,
            timeout=15,
        )
        if resp.status_code == 401:
            raise RuntimeError("[Cafe24] 토큰 만료 - 재인증 필요")
        if resp.status_code != 200:
            raise RuntimeError(f"[Cafe24] 주문 조회 실패 ({resp.status_code}): {resp.text[:200]}")

        data = resp.json()
        batch = data.get("orders") or []
        if not batch:
            break

        for o in batch:
            payment = int(float(o.get("payment_amount", 0) or 0))
            orders.append({
                "order_id":       str(o.get("order_id", "")),
                "product_name":   "",
                "quantity":       1,
                "unit_price":     payment,
                "payment_amount": payment,
                "order_status":   o.get("paid", "") or "",
                "order_date":     o.get("order_date", ""),
            })

        if len(batch) < limit:
            break
        offset += limit
        time.sleep(0.2)

    return orders


def _extract_product_name(order: dict) -> str:
    items = order.get("items") or []
    if items:
        return items[0].get("product_name", "")
    return order.get("product_name", "")


def _extract_quantity(order: dict) -> int:
    items = order.get("items") or []
    if items:
        return sum(int(i.get("quantity", 0)) for i in items)
    return 0


def fetch(project: str, creds: dict, days: int = None) -> list[dict]:
    """외부 진입점: creds = {mall_id, client_id, client_secret}, days=조회일수"""
    access_token = _get_access_token(project, creds)
    orders = _fetch_orders(creds["mall_id"], access_token, days=days)
    print(f"  [Cafe24] 주문 {len(orders)}건 수집")
    return orders
