# 스마트스토어 API 연결 확인판 (MVP)

네이버 커머스 API 연결이 실제로 뚫렸는지 확인하기 위한 최소 구현입니다.

---

## 준비 체크리스트 (시작 전 필수)

- [ ] [apicenter.commerce.naver.com](https://apicenter.commerce.naver.com) 접속
- [ ] 애플리케이션 등록 (애플리케이션 관리 > 애플리케이션 등록)
- [ ] API 권한 그룹 신청: **주문** 관련 권한 승인 필요 (공식 콘솔 확인 필요)
- [ ] Client ID / Client Secret 복사
- [ ] IP 화이트리스트 등록 여부 확인 (콘솔에서 확인 필요)

---

## 설치

```bash
# 1. 이 폴더로 이동
cd naver-smartstore-mvp

# 2. 패키지 설치
pip install -r requirements.txt

# 3. .env 파일 생성
copy .env.example .env
```

`.env` 파일을 열어 `NAVER_CLIENT_ID`와 `NAVER_CLIENT_SECRET`을 입력하세요.

---

## 실행 순서

### 1단계 - 인증 테스트
```bash
python scripts/test_auth.py
```
✅ 성공: `토큰 발급 성공` 메시지
❌ 실패: 오류 메시지 확인 → 아래 오류 대응표 참고

### 2단계 - 주문 1회 수집
```bash
python scripts/run_once.py
```
✅ 성공: `N건 신규 저장` 메시지

### 3단계 - 웹 화면 실행
```bash
streamlit run streamlit_app.py
```
브라우저에서 `http://localhost:8501` 접속

---

## 오류 대응표

| 오류 | 원인 | 해결 |
|------|------|------|
| `.env 파일에 다음 항목을 입력해주세요` | CLIENT_ID/SECRET 미입력 | .env 파일 확인 |
| `토큰 발급 실패 (HTTP 401)` | Client ID/Secret 오류 | 콘솔에서 재확인 |
| `토큰 발급 실패 (HTTP 403)` | IP 차단 또는 권한 부족 | IP 화이트리스트 확인, 권한 그룹 승인 확인 |
| `인증 오류(401)` (주문 조회 시) | 토큰 만료 | 다시 실행 (토큰 자동 재발급) |
| `권한 부족(403)` (주문 조회 시) | 주문 API 권한 미승인 | 콘솔에서 권한 그룹 재확인 |
| `수집된 주문이 없습니다` | 조회 기간 내 변경 주문 없음 | `.env`의 `FETCH_DAYS` 값 늘리기 |
| `orders.db 파일이 없습니다` | run_once.py 미실행 | `python scripts/run_once.py` 먼저 실행 |
| `streamlit: command not found` | streamlit 미설치 | `pip install streamlit` |

---

## 파일 구조

```
naver-smartstore-mvp/
├── .env.example          # 환경변수 샘플
├── .env                  # 실제 입력 (직접 생성)
├── requirements.txt      # 패키지 목록
├── streamlit_app.py      # 웹 화면
├── orders.db             # SQLite DB (run_once.py 실행 후 생성됨)
├── app/
│   ├── config.py         # 환경변수 로딩
│   ├── auth.py           # 토큰 발급
│   ├── client.py         # API 호출 공통
│   ├── fetch_orders.py   # 주문 조회
│   ├── db.py             # DB 저장
│   └── metrics.py        # 집계 계산
└── scripts/
    ├── test_auth.py      # 인증만 테스트
    └── run_once.py       # 1회 수집 실행
```

---

## 다음 단계 (MVP 성공 후)

1. **자동 스케줄**: Windows 작업 스케줄러로 run_once.py 주기 실행
2. **기간 확장**: 최근 30일 전체 백필
3. **상태 필터**: 결제완료 주문만 집계
4. **수수료 계산**: 네이버페이 수수료 차감 후 순이익 표시
5. **기존 sales-dashboard 통합**: 다른 채널과 합산
