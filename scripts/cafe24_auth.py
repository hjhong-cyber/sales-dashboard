"""Cafe24 최초 인증 스크립트 - 프로젝트별 1회 실행"""
import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.config import PROJECTS, get_cafe24_creds
from app.channels.cafe24 import _authorize, _save_token

project_key = sys.argv[1] if len(sys.argv) > 1 else "glener"
project_name = PROJECTS.get(project_key, {}).get("name", project_key)

print(f"=== [{project_name}] Cafe24 인증 ===\n")

creds = get_cafe24_creds(project_key)
if not creds:
    print(f"[오류] .env에 {project_key.upper()}_CAFE24_* 설정이 없습니다.")
    sys.exit(1)

token_data = _authorize(project_key, creds)
token_data["expires_at"] = time.time() + token_data.get("expires_in", 7200)
_save_token(project_key, token_data)
print(f"\n[완료] {project_name} Cafe24 토큰 저장 완료")
print("이제 python scripts/run_once.py 를 실행하면 주문이 수집됩니다.")
