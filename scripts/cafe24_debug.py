"""Cafe24 API 진단 스크립트"""
import sys
import os
import json
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.config import get_cafe24_creds
from app.channels.cafe24 import _get_access_token

project_key = sys.argv[1] if len(sys.argv) > 1 else "glener"
creds = get_cafe24_creds(project_key)
if not creds:
    print(f"[오류] .env에 {project_key.upper()}_CAFE24_* 설정이 없습니다.")
    sys.exit(1)

mall_id = creds["mall_id"]
print(f"mall_id: {mall_id}")

access_token = _get_access_token(project_key, creds)
print(f"access_token: {access_token[:20]}...")

import requests

# 테스트할 API 버전 목록
versions = ["2024-09-01", "2023-09-01", "2022-09-01", "2021-09-01"]
# 테스트할 엔드포인트
endpoints = [
    "/api/v2/shops",
    "/api/v2/orders",
    "/api/v2/products",
]

print("\n=== API 버전별 테스트 ===")
for version in versions:
    print(f"\n--- Version: {version} ---")
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Cafe24-Api-Version": version,
    }
    for ep in endpoints:
        url = f"https://{mall_id}.cafe24api.com{ep}"
        params = {"shop_no": 1, "limit": 1}
        if "orders" in ep:
            from datetime import datetime, timedelta
            today = datetime.now()
            params["start_date"] = (today - timedelta(days=1)).strftime("%Y-%m-%d")
            params["end_date"] = today.strftime("%Y-%m-%d")
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=10)
            print(f"  {ep}: {resp.status_code} - {resp.text[:100]}")
        except Exception as e:
            print(f"  {ep}: ERROR - {e}")
        time.sleep(0.3)

print("\n=== 버전 없이 테스트 ===")
headers_no_version = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json",
}
for ep in endpoints:
    url = f"https://{mall_id}.cafe24api.com{ep}"
    params = {"shop_no": 1, "limit": 1}
    if "orders" in ep:
        from datetime import datetime, timedelta
        today = datetime.now()
        params["start_date"] = (today - timedelta(days=7)).strftime("%Y-%m-%d")
        params["end_date"] = today.strftime("%Y-%m-%d")
    try:
        resp = requests.get(url, headers=headers_no_version, params=params, timeout=10)
        print(f"  {ep}: {resp.status_code} - {resp.text[:150]}")
    except Exception as e:
        print(f"  {ep}: ERROR - {e}")
    time.sleep(0.3)

print("\n=== 저장된 토큰 정보 ===")
token_path = f".cafe24_tokens/{project_key}.json"
if os.path.exists(token_path):
    with open(token_path) as f:
        token_data = json.load(f)
    print(f"scope: {token_data.get('scope', 'N/A')}")
    print(f"expires_at: {token_data.get('expires_at', 'N/A')} (now: {time.time():.0f})")
    expires_in = token_data.get('expires_at', 0) - time.time()
    print(f"expires_in: {expires_in:.0f}s")
