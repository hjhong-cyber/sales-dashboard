"""네이버 커머스 API 토큰 발급"""
import time
import base64
import requests
import bcrypt
from app.config import CLIENT_ID, CLIENT_SECRET, BASE_URL


def _make_signature(timestamp: int) -> str:
    """
    bcrypt 전자서명 생성 (네이버 커머스 API 공식 방식)

    - password  : CLIENT_ID + "_" + timestamp(밀리초 문자열)
    - salt      : CLIENT_SECRET 전체를 그대로 bcrypt salt로 사용
                  (client_secret 형식이 "$2a$04$..." 인 bcrypt salt 문자열)
    - 결과       : bcrypt.hashpw() 반환값을 base64 인코딩한 문자열

    주의: HMAC-SHA256은 이 API에서 동작하지 않습니다.
    """
    password = f"{CLIENT_ID}_{timestamp}"
    hashed = bcrypt.hashpw(password.encode("utf-8"), CLIENT_SECRET.encode("utf-8"))
    return base64.b64encode(hashed).decode("utf-8")


def get_token() -> str:
    """액세스 토큰 발급 후 반환"""
    timestamp = int(time.time() * 1000)  # 밀리초 (13자리)
    signature = _make_signature(timestamp)

    url = f"{BASE_URL}/v1/oauth2/token"
    # 네이버 커머스 API는 JSON body가 아닌 query string(form-urlencoded) 방식 필요
    params = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "timestamp": timestamp,
        "client_secret_sign": signature,
        "type": "SELF",
    }

    resp = requests.post(
        url,
        params=params,
        headers={"content-type": "application/x-www-form-urlencoded"},
        timeout=10,
    )

    if resp.status_code != 200:
        raise RuntimeError(
            f"토큰 발급 실패 (HTTP {resp.status_code})\n"
            f"응답: {resp.text}\n"
            f"확인: CLIENT_ID/SECRET이 맞는지, API 권한 그룹이 승인됐는지 확인하세요."
        )

    token = resp.json().get("access_token")
    if not token:
        raise RuntimeError(f"토큰이 응답에 없습니다. 응답 전체: {resp.json()}")

    print("[OK] 토큰 발급 성공")
    return token
