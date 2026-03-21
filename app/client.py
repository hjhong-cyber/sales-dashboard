"""네이버 커머스 API 공통 호출 함수"""
import requests
from app.config import BASE_URL


def api_get(token: str, path: str, params: dict = None) -> dict:
    """GET 요청"""
    url = f"{BASE_URL}{path}"
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(url, headers=headers, params=params, timeout=15)
    _raise_if_error(resp)
    return resp.json()


def api_post(token: str, path: str, body: dict) -> dict:
    """POST 요청"""
    url = f"{BASE_URL}{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    resp = requests.post(url, headers=headers, json=body, timeout=15)
    _raise_if_error(resp)
    return resp.json()


def _raise_if_error(resp: requests.Response):
    if resp.status_code == 401:
        raise RuntimeError("인증 오류(401): 토큰이 만료됐거나 권한이 없습니다.")
    if resp.status_code == 403:
        raise RuntimeError("권한 부족(403): API 권한 그룹을 확인하세요.")
    if resp.status_code != 200:
        raise RuntimeError(
            f"API 오류 (HTTP {resp.status_code}): {resp.text[:300]}"
        )
