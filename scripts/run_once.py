"""전체 프로젝트 × 활성 채널 수집 실행"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.config import PROJECTS, get_naver_creds, get_cafe24_creds, get_coupang_creds
from app.db import init_db, save_orders

def run():
    print("=== 통합 매출 데이터 수집 시작 ===\n")
    init_db()

    for project_key, project_info in PROJECTS.items():
        project_name = project_info["name"]
        print(f"\n▶ [{project_name}] 수집 시작")

        # 네이버
        naver_creds = get_naver_creds(project_key)
        if naver_creds:
            try:
                from app.channels import naver
                orders = naver.fetch(naver_creds)
                saved = save_orders(project_key, "naver", orders)
                print(f"  [네이버] {saved}건 신규 저장 (전체 {len(orders)}건)")
            except Exception as e:
                print(f"  [네이버] 오류: {e}")
        else:
            print(f"  [네이버] 자격증명 없음 - 건너뜀")

        # Cafe24
        cafe24_creds = get_cafe24_creds(project_key)
        if cafe24_creds:
            try:
                from app.channels import cafe24
                orders = cafe24.fetch(project_key, cafe24_creds)
                saved = save_orders(project_key, "cafe24", orders)
                print(f"  [Cafe24] {saved}건 신규 저장 (전체 {len(orders)}건)")
            except Exception as e:
                print(f"  [Cafe24] 오류: {e}")
        else:
            print(f"  [Cafe24] 자격증명 없음 - 건너뜀")

        # 쿠팡 (자격증명만 확인, 구현 예정)
        coupang_creds = get_coupang_creds(project_key)
        if coupang_creds:
            print(f"  [쿠팡] 연동 준비 중...")
        else:
            print(f"  [쿠팡] 자격증명 없음 - 건너뜀")

    print("\n=== 수집 완료 ===")
    print("다음: streamlit run streamlit_app.py")

if __name__ == "__main__":
    run()
