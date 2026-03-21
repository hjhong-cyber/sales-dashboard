"""인증 테스트 - 이 파일만 실행해서 토큰 발급이 되는지 먼저 확인"""
import sys
import os

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.config import check_config
from app.auth import get_token

if __name__ == "__main__":
    print("=== 네이버 커머스 API 인증 테스트 ===")
    try:
        check_config()
        token = get_token()
        print(f"토큰 앞 20자: {token[:20]}...")
        print("\n[성공] 인증 성공! 다음 단계로 넘어가세요.")
    except Exception as e:
        print(f"\n[실패] {e}")
        sys.exit(1)
