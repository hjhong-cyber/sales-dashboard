"""통합 매출 대시보드 - 멀티 프로젝트 × 멀티 채널"""
import os
import subprocess
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from datetime import date, datetime

if not os.path.exists("orders.db"):
    from app.db import init_db
    init_db()

from app.metrics import get_summary, get_project_channels, CHANNEL_LABELS
from app.config import PROJECTS

st.set_page_config(page_title="매출 대시보드", layout="wide")

# ── 채널 색상 ──────────────────────────────────────
CH_COLORS = {
    "naver":          "#03C75A",
    "cafe24":         "#3D5AFE",
    "coupang":        "#E31837",
    "shopify":        "#96BF48",
    "cjonstyle":      "#ED1C24",
    "cafe24_youtube": "#FF0000",
    "zvzo":           "#FF6B35",
    "shinsegae":      "#C8102E",
    "gsshop":         "#FF4081",
    "kurly":          "#5F0080",
    "lotteon":        "#E30613",
    "kakao":          "#FEE500",
    "woorisiktuk":    "#FF8C42",
    "toss":           "#0064FF",
    "wellstory":      "#00897B",
    "shinsegaetv":    "#9C27B0",
    "11st":           "#FF5722",
    "gmarket":        "#00B259",
    "auction":        "#F57C00",
    "others":         "#555555",
    # 프로젝트 색상 (전체 대시보드용)
    "glener":         "#3D5AFE",
    "gravyploof":     "#FF6B35",
    "ballwatch":      "#00BCD4",
    "xexymix":        "#E91E63",
    "groupbuy":       "#FFC107",
    "themango":       "#4CAF50",
    "lecture":        "#FF9800",
    "excel":          "#4CAF50",
    "mango_total":    "#FF9800",
}

st.markdown("""
<style>
.stApp { background-color: #0e1117; }

/* 카드 스타일 */
.metric-card {
    background: linear-gradient(135deg, #1e2130 0%, #262b3e 100%);
    border-radius: 16px;
    padding: 24px 28px;
    border: 1px solid rgba(255,255,255,0.06);
}
.metric-card .label {
    color: #8b8fa3;
    font-size: 0.85rem;
    font-weight: 500;
    margin-bottom: 6px;
}
.metric-card .value {
    color: #ffffff;
    font-size: 2rem;
    font-weight: 800;
    letter-spacing: -0.5px;
}
.metric-card .sub {
    color: #8b8fa3;
    font-size: 0.8rem;
    margin-top: 4px;
}

/* 구분선 */
hr { border-color: #1e2130 !important; margin: 0.8rem 0 !important; }

/* 탭 스타일 */
.stTabs [data-baseweb="tab-list"] {
    gap: 0px;
    background-color: #1e2130;
    border-radius: 12px;
    padding: 4px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 10px;
    padding: 10px 24px;
    font-weight: 600;
    font-size: 0.95rem;
    color: #8b8fa3;
}
.stTabs [aria-selected="true"] {
    background-color: #3D5AFE !important;
    color: white !important;
}

/* 제목 */
h1 { color: #fff !important; font-weight: 800 !important; }
h3 { color: #c0c4d6 !important; font-weight: 600 !important; font-size: 1rem !important; }
h4 { color: #e0e0e0 !important; }

/* metric 기본 스타일 숨기기 */
[data-testid="stMetricLabel"] { display: none; }
[data-testid="stMetricValue"] { display: none; }
</style>
""", unsafe_allow_html=True)


def fmt_amount(amount: int) -> str:
    """금액을 억/만 단위로 포맷"""
    if amount >= 100_000_000:
        return f"₩{amount / 100_000_000:.1f}억"
    if amount >= 10_000_000:
        return f"₩{amount / 10_000:,.0f}만"
    return f"₩{amount:,}"


# ── 차트 컴포넌트 ──────────────────────────────────

def metric_card(label: str, amount: int, sub: str = ""):
    """다크 카드 스타일 메트릭"""
    sub_html = f'<div class="sub">{sub}</div>' if sub else ""
    st.markdown(f"""
    <div class="metric-card">
        <div class="label">{label}</div>
        <div class="value">₩{amount:,}</div>
        {sub_html}
    </div>
    """, unsafe_allow_html=True)


def channel_donut_with_legend(channels_data: list, center_label: str, center_amount: int, key: str):
    """큰 도넛 차트 + 중앙 금액 + 하단 범례"""
    # 데이터 없으면 빈 도넛 표시 (컬럼 높이 맞춤)
    if not channels_data:
        channels_data = [{"channel": "_empty", "label": "-", "amount": 1}]

    labels = [ch["label"] for ch in channels_data]
    amounts = [ch["amount"] for ch in channels_data]
    colors = [CH_COLORS.get(ch["channel"], "#666") for ch in channels_data]
    total = sum(amounts) or 1

    fig = go.Figure(go.Pie(
        labels=labels,
        values=amounts,
        hole=0.65,
        marker=dict(colors=colors, line=dict(color="#0e1117", width=3)),
        textinfo="none",
        hovertemplate="<b>%{label}</b><br>₩%{value:,.0f}<br>%{percent}<extra></extra>",
    ))

    # 중앙 텍스트
    fig.add_annotation(
        text=f"<b>{fmt_amount(center_amount)}</b>",
        x=0.5, y=0.5, font=dict(size=22, color="white"),
        showarrow=False, xref="paper", yref="paper",
    )

    fig.update_layout(
        height=260,
        margin=dict(t=10, b=10, l=10, r=10),
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True, key=key)

    # 범례 + 금액 (고정 높이로 라인 맞춤)
    legend_items = ""
    for ch, amt, color in zip(channels_data, amounts, colors):
        pct = amt / total * 100
        legend_items += (
            f'<span style="display:inline-flex;align-items:center;gap:5px;margin-right:14px;font-size:0.82rem;color:#c0c4d6;">'
            f'<span style="width:9px;height:9px;border-radius:50%;background:{color};display:inline-block;"></span>'
            f'<b>{ch["label"]}</b> ₩{amt:,} ({pct:.0f}%)'
            f'</span>'
        )
    st.markdown(f'<div style="min-height:80px;line-height:1.8;">{legend_items}</div>', unsafe_allow_html=True)


def daily_chart(data: dict, prefix: str, height=300):
    if not data["daily"]:
        return

    # 최근 30일만 표시
    recent = data["daily"][-30:]
    days = [r["day"][5:] for r in recent]  # MM-DD만
    amounts = [r["amount"] for r in recent]
    counts = [r["count"] for r in recent]

    fig = go.Figure()
    # 영역 채우기
    fig.add_trace(go.Scatter(
        x=days, y=amounts,
        fill="tozeroy",
        fillcolor="rgba(61,90,254,0.15)",
        line=dict(color="#3D5AFE", width=2.5),
        mode="lines",
        hovertemplate="<b>%{x}</b><br>₩%{y:,.0f}<extra></extra>",
    ))
    # 포인트 (hover용)
    fig.add_trace(go.Scatter(
        x=days, y=amounts,
        mode="markers",
        marker=dict(color="#3D5AFE", size=6, line=dict(color="#0e1117", width=1.5)),
        customdata=counts,
        hovertemplate="<b>%{x}</b><br>₩%{y:,.0f}<br>%{customdata}건<extra></extra>",
        showlegend=False,
    ))

    fig.update_layout(
        xaxis=dict(tickangle=-45, tickfont=dict(size=9, color="#555"),
                   gridcolor="rgba(255,255,255,0.03)", showgrid=False),
        yaxis=dict(tickformat=",", gridcolor="rgba(255,255,255,0.05)",
                   tickfont=dict(color="#555")),
        margin=dict(t=10, b=50, l=60, r=10),
        height=height,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True, key=f"{prefix}_daily")


def monthly_chart(data: dict, prefix: str, height=280):
    if not data["monthly"]:
        return

    months = [r["month"] for r in data["monthly"]]
    amounts = [r["amount"] for r in data["monthly"]]
    # 바 위에 금액 라벨
    labels = [fmt_amount(a) for a in amounts]

    fig = go.Figure(go.Bar(
        x=months, y=amounts,
        marker=dict(
            color=amounts,
            colorscale=[[0, "#1a237e"], [0.5, "#3D5AFE"], [1, "#448AFF"]],
            cornerradius=6,
        ),
        text=labels,
        textposition="outside",
        textfont=dict(color="#8b8fa3", size=12, family="Arial"),
        hovertemplate="<b>%{x}</b><br>₩%{y:,.0f}<extra></extra>",
    ))
    fig.update_layout(
        xaxis=dict(type="category", tickfont=dict(size=11, color="#888")),
        yaxis=dict(visible=False),
        margin=dict(t=30, b=30, l=10, r=10),
        height=height,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        bargap=0.35,
    )
    st.plotly_chart(fig, use_container_width=True, key=f"{prefix}_monthly")


# ── 도넛용 데이터 가공 (상위 N개 + 기타) ──────────

def _top_channels(channels_data: list, top_n: int = 5) -> list:
    """매출 상위 N개만 표시, 나머지는 '기타'로 묶기"""
    if len(channels_data) <= top_n:
        return [c for c in channels_data if c["amount"] > 0]

    sorted_data = sorted(channels_data, key=lambda x: x["amount"], reverse=True)
    top = sorted_data[:top_n]
    others_amount = sum(c["amount"] for c in sorted_data[top_n:])

    result = [c for c in top if c["amount"] > 0]
    if others_amount > 0:
        result.append({"channel": "others", "label": "기타", "amount": others_amount})
    return result


# ── 프로젝트 대시보드 ─────────────────────────────

def show_excel_upload(project_key: str, project_name: str):
    """엑셀 업로드 → 매출조회 버튼으로 간단하게"""
    from app.db import get_conn, save_orders

    # 업로드 영역 스타일: 다크 테마 + 한글 + 작은 사이즈
    st.markdown(f"""
    <style>
    div[data-testid="stFileUploader"] > section {{
        background-color: #1e2130 !important;
        border: 1px dashed rgba(255,255,255,0.15) !important;
        border-radius: 12px !important;
        padding: 12px 16px !important;
    }}
    div[data-testid="stFileUploader"] > section > div {{
        color: #8b8fa3 !important;
    }}
    div[data-testid="stFileUploader"] > section button {{
        background-color: #3D5AFE !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
    }}
    div[data-testid="stFileUploaderDropzone"] > div > span {{
        visibility: hidden;
    }}
    div[data-testid="stFileUploaderDropzone"] > div > span::after {{
        content: "매출데이터 업로드";
        visibility: visible;
        color: #8b8fa3;
        font-size: 0.85rem;
    }}
    div[data-testid="stFileUploaderDropzone"] > div > small {{
        display: none;
    }}
    </style>
    """, unsafe_allow_html=True)

    _, col_upload, col_btn = st.columns([2, 1.2, 0.8])
    with col_upload:
        uploaded = st.file_uploader(
            "매출데이터 업로드",
            type=["xlsx", "xls"],
            key=f"{project_key}_upload",
            label_visibility="collapsed",
        )
    with col_btn:
        btn = st.button("매출조회", key=f"{project_key}_save_btn", type="primary", use_container_width=True)

    if uploaded and btn:
        try:
            xls = pd.ExcelFile(uploaded)
        except Exception as e:
            st.error(f"엑셀 읽기 실패: {e}")
            return

        # 모든 시트에서 B열(날짜), K열(결제금액) 읽어서 합산
        orders = []
        for sheet_name in xls.sheet_names:
            try:
                df = pd.read_excel(xls, sheet_name=sheet_name, header=None)
            except Exception:
                continue

            data_df = df.iloc[1:].copy()
            data_df = data_df.dropna(subset=[1, 10])

            for idx, row in data_df.iterrows():
                try:
                    raw_date = row[1]
                    if isinstance(raw_date, datetime):
                        order_date = raw_date.strftime("%Y-%m-%d")
                    else:
                        order_date = str(raw_date)[:10]

                    amount = int(float(row[10]))
                    order_id = f"{project_key}_{sheet_name}_{order_date}_{idx}"

                    orders.append({
                        "order_id": order_id,
                        "product_name": str(row[4]) if pd.notna(row.get(4)) else "",
                        "quantity": 1,
                        "unit_price": amount,
                        "payment_amount": amount,
                        "order_status": "paid",
                        "order_date": order_date,
                    })
                except (ValueError, TypeError):
                    continue

        if not orders:
            st.warning("유효한 데이터가 없습니다.")
            return

        with get_conn() as conn:
            conn.execute("DELETE FROM orders WHERE project=? AND channel='excel'", (project_key,))
        save_orders(project_key, "excel", orders)
        st.rerun()


REFRESH_DAYS = 15  # 갱신 시 최근 N일만 조회

# ── 공동구매 Google Sheets 연동 ───────────────────
GROUPBUY_SHEET_ID = "1-0DhO5cNhhq5_kaOhN9RDzg1WSocebvSp2sL3KGt_38"
GROUPBUY_GID = "382400914"


def fetch_groupbuy_from_sheets():
    """공구관리시스템 스프레드시트에서 매출 데이터 가져오기"""
    from app.db import get_conn, save_orders

    url = f"https://docs.google.com/spreadsheets/d/{GROUPBUY_SHEET_ID}/gviz/tq?tqx=out:csv&gid={GROUPBUY_GID}"
    try:
        df = pd.read_csv(url, header=None)
    except Exception as e:
        return f"스프레드시트 읽기 실패: {e}"

    orders = []
    for idx, row in df.iterrows():
        # NO 컬럼(0번)이 숫자인 행만 데이터
        try:
            no = int(row[0])
        except (ValueError, TypeError):
            continue

        try:
            revenue = int(float(str(row[9]).replace(",", "")))
        except (ValueError, TypeError):
            continue

        if revenue <= 0:
            continue

        # 개시일을 order_date로 사용
        start_date = str(row[5])[:10] if pd.notna(row[5]) else ""
        product_name = str(row[4]) if pd.notna(row[4]) else ""
        seller = str(row[2]) if pd.notna(row[2]) else ""
        company = str(row[3]) if pd.notna(row[3]) else ""

        order_id = f"groupbuy_sheets_{no}"
        orders.append({
            "order_id": order_id,
            "product_name": f"{company} - {product_name}" if company else product_name,
            "quantity": 1,
            "unit_price": revenue,
            "payment_amount": revenue,
            "order_status": str(row[14]) if pd.notna(row[14]) else "paid",
            "order_date": start_date,
        })

    if not orders:
        return "유효한 데이터가 없습니다."

    # 기존 sheets 데이터 삭제 후 새로 저장
    with get_conn() as conn:
        conn.execute("DELETE FROM orders WHERE project='groupbuy' AND channel='sheets'")
    saved = save_orders("groupbuy", "sheets", orders)
    return f"공동구매: {len(orders)}건 조회, {saved}건 저장 완료"


def _auto_push():
    """갱신 후 orders.db를 자동으로 git commit & push (Streamlit Cloud 반영)"""
    try:
        repo_dir = os.path.dirname(os.path.abspath(__file__))
        subprocess.run(["git", "add", "orders.db"], cwd=repo_dir, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", f"auto: 매출 데이터 갱신 ({date.today()})"],
            cwd=repo_dir, check=True, capture_output=True,
        )
        subprocess.run(["git", "push"], cwd=repo_dir, check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError:
        return False

def _refresh_project_data(project_key: str):
    """프로젝트의 API 채널 데이터만 갱신 (수동입력/엑셀 유지, 최근 15일)"""
    from app.config import get_naver_creds, get_cafe24_creds
    from app.db import save_orders

    results = []

    # 공동구매: Google Sheets에서 가져오기
    if project_key == "groupbuy":
        result = fetch_groupbuy_from_sheets()
        results.append(result)
        return results

    # 네이버
    naver_creds = get_naver_creds(project_key)
    if naver_creds:
        try:
            from app.channels import naver
            orders = naver.fetch(naver_creds, days=REFRESH_DAYS)
            saved = save_orders(project_key, "naver", orders)
            results.append(f"네이버: {len(orders)}건 조회, {saved}건 신규")
        except Exception as e:
            results.append(f"네이버: 오류 - {e}")

    # Cafe24
    cafe24_creds = get_cafe24_creds(project_key)
    if cafe24_creds:
        try:
            from app.channels import cafe24
            orders = cafe24.fetch(project_key, cafe24_creds, days=REFRESH_DAYS)
            saved = save_orders(project_key, "cafe24", orders)
            results.append(f"Cafe24: {len(orders)}건 조회, {saved}건 신규")
        except Exception as e:
            results.append(f"Cafe24: 오류 - {e}")

    return results


def show_project_dashboard(project_key: str, project_name: str):
    # 타이틀 + 갱신 버튼
    col_title, col_refresh = st.columns([5, 1])
    with col_title:
        st.title(f"{project_name}")
    with col_refresh:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("매출 갱신", key=f"{project_key}_refresh", type="secondary", use_container_width=True):
            with st.spinner("매출 데이터 갱신 중..."):
                results = _refresh_project_data(project_key)
            if results:
                st.toast(" | ".join(results))
                if _auto_push():
                    st.toast("클라우드 대시보드에 반영 완료!")
            else:
                st.toast("갱신할 API 채널이 없습니다.")
            st.rerun()

    total_data = get_summary(project=project_key, channel=None)
    channels = get_project_channels(project_key)

    # 채널별 데이터 미리 수집 (중복 호출 방지)
    ch_summaries = {}
    for ch in channels:
        ch_summaries[ch] = get_summary(project=project_key, channel=ch)

    # 채널을 연도 매출 순으로 정렬
    channels_sorted = sorted(channels, key=lambda c: ch_summaries[c]["year"]["amount"], reverse=True)

    # ── 상단 카드: 엑셀 프로젝트는 2컬럼(연도/당월), 나머지는 3컬럼 ──
    is_excel_project = project_key in EXCEL_UPLOAD_PROJECTS

    if is_excel_project:
        col1, col2 = st.columns(2)
    else:
        col1, col2, col3 = st.columns(3)

    with col1:
        year_channels = [
            {"channel": ch, "label": CHANNEL_LABELS.get(ch, ch), "amount": ch_summaries[ch]["year"]["amount"]}
            for ch in channels_sorted
        ]
        channel_donut_with_legend(
            _top_channels(year_channels),
            center_label=f"{total_data['this_year']}년",
            center_amount=total_data["year"]["amount"],
            key=f"{project_key}_year_donut",
        )
        metric_card(f"{total_data['this_year']}년 매출", total_data["year"]["amount"])

    with col2:
        month_channels = [
            {"channel": ch, "label": CHANNEL_LABELS.get(ch, ch), "amount": ch_summaries[ch]["month"]["amount"]}
            for ch in channels_sorted
        ]
        channel_donut_with_legend(
            _top_channels(month_channels),
            center_label=total_data["this_month"],
            center_amount=total_data["month"]["amount"],
            key=f"{project_key}_month_donut",
        )
        metric_card(f"{total_data['this_month']} 매출", total_data["month"]["amount"])

    if not is_excel_project:
        with col3:
            today_str = date.today().strftime("%m/%d")
            today_channels = [
                {"channel": ch, "label": CHANNEL_LABELS.get(ch, ch), "amount": ch_summaries[ch]["today"]["amount"]}
                for ch in channels_sorted
            ]
            channel_donut_with_legend(
                _top_channels(today_channels),
                center_label="오늘",
                center_amount=total_data["today"]["amount"],
                key=f"{project_key}_today_donut",
            )
            metric_card(f"오늘 ({today_str})", total_data["today"]["amount"])

    st.markdown("<br>", unsafe_allow_html=True)
    st.divider()

    # ── 채널별 월 매출 테이블 ──
    st.markdown("#### 채널별 월 매출")
    _channel_monthly_table(project_key, channels_sorted, ch_summaries)

    # ── 수동 매출 입력 ──
    _manual_sales_input(project_key)

    # ── 수동 입력 데이터 관리 ──
    _manual_data_manager(project_key)

    st.divider()

    # ── 채널별 상세 탭 (매출순) ──
    if not channels_sorted:
        return

    channel_labels = [CHANNEL_LABELS.get(ch, ch) for ch in channels_sorted]
    channel_tabs = st.tabs(channel_labels)

    for ch_tab, ch_key in zip(channel_tabs, channels_sorted):
        with ch_tab:
            ch_data = ch_summaries[ch_key]

            c1, c2, c3 = st.columns(3)
            with c1:
                metric_card(f"{ch_data['this_year']}년", ch_data["year"]["amount"])
            with c2:
                metric_card(f"{ch_data['this_month']}", ch_data["month"]["amount"])
            with c3:
                metric_card("오늘", ch_data["today"]["amount"])

            st.markdown("<br>", unsafe_allow_html=True)

            # API 채널만 일별 차트 표시 (사방넷 데이터는 월별만)
            if ch_data["daily"] and len(ch_data["daily"]) > 1:
                st.markdown("#### 일별 추이")
                daily_chart(ch_data, prefix=f"{project_key}_{ch_key}")

            st.markdown("#### 월별 추이")
            monthly_chart(ch_data, prefix=f"{project_key}_{ch_key}")

            st.caption(f"마지막 수집: {ch_data['last_saved']}")


def _channel_monthly_table(project_key: str, channels_sorted: list, ch_summaries: dict):
    """채널별 월 매출 요약 테이블"""
    from app.db import get_conn

    # 모든 월 가져오기
    with get_conn() as conn:
        month_rows = conn.execute("""
            SELECT DISTINCT SUBSTR(order_date,1,7) AS month
            FROM orders WHERE project=? AND order_date != ''
            ORDER BY month DESC LIMIT 6
        """, (project_key,)).fetchall()
    months = [r[0] for r in month_rows]

    if not months:
        return

    # 테이블 HTML 생성
    html = '<div style="overflow-x:auto;"><table style="width:100%;border-collapse:collapse;font-size:0.85rem;">'
    # 헤더
    html += '<tr style="border-bottom:2px solid #333;">'
    html += '<th style="text-align:left;padding:8px 12px;color:#8b8fa3;">채널</th>'
    for m in months:
        html += f'<th style="text-align:right;padding:8px 12px;color:#8b8fa3;">{m}</th>'
    html += '</tr>'

    # 데이터 행
    with get_conn() as conn:
        for ch in channels_sorted:
            label = CHANNEL_LABELS.get(ch, ch)
            color = CH_COLORS.get(ch, "#666")
            html += f'<tr style="border-bottom:1px solid #1e2130;">'
            html += f'<td style="padding:8px 12px;"><span style="color:{color};font-weight:700;">●</span> {label}</td>'
            for m in months:
                row = conn.execute("""
                    SELECT COALESCE(SUM(payment_amount),0) FROM orders
                    WHERE project=? AND channel=? AND SUBSTR(order_date,1,7)=?
                """, (project_key, ch, m)).fetchone()
                amt = row[0]
                display = f"₩{amt:,}" if amt > 0 else "-"
                html += f'<td style="text-align:right;padding:8px 12px;color:#c0c4d6;">{display}</td>'
            html += '</tr>'

    # 합계 행
    html += '<tr style="border-top:2px solid #3D5AFE;">'
    html += '<td style="padding:8px 12px;font-weight:800;color:#fff;">합계</td>'
    with get_conn() as conn:
        for m in months:
            row = conn.execute("""
                SELECT COALESCE(SUM(payment_amount),0) FROM orders
                WHERE project=? AND SUBSTR(order_date,1,7)=?
            """, (project_key, m)).fetchone()
            html += f'<td style="text-align:right;padding:8px 12px;font-weight:800;color:#fff;">₩{row[0]:,}</td>'
    html += '</tr>'

    html += '</table></div>'
    st.markdown(html, unsafe_allow_html=True)


def _manual_sales_input(project_key: str):
    """채널명 + 월 + 매출금액 여러 행 수동 입력"""
    from app.db import get_conn, save_orders

    # 행 수 관리
    row_count_key = f"{project_key}_manual_rows"
    if row_count_key not in st.session_state:
        st.session_state[row_count_key] = 1

    with st.expander("매출 수동 입력", expanded=False):
        # 입력 행들
        for i in range(st.session_state[row_count_key]):
            col1, col2, col3 = st.columns([2, 2, 2])
            with col1:
                st.text_input("채널명" if i == 0 else "채널명 ", placeholder="예: 홈쇼핑", key=f"{project_key}_ch_{i}", label_visibility="visible" if i == 0 else "collapsed")
            with col2:
                st.text_input("월 (YYYY-MM)" if i == 0 else "월 ", placeholder="예: 2026-03", key=f"{project_key}_month_{i}", label_visibility="visible" if i == 0 else "collapsed")
            with col3:
                st.number_input("매출금액 (원)" if i == 0 else "매출금액 ", min_value=0, step=10000, key=f"{project_key}_amt_{i}", label_visibility="visible" if i == 0 else "collapsed")

        # 행 추가 + 입력완료 버튼
        col_add, _, col_submit = st.columns([1, 2, 1])
        with col_add:
            if st.button("+ 행 추가", key=f"{project_key}_add_row"):
                st.session_state[row_count_key] += 1
                st.rerun()
        with col_submit:
            submit = st.button("입력완료", key=f"{project_key}_manual_btn", type="primary", use_container_width=True)

        if submit:
            label_to_key = {v: k for k, v in CHANNEL_LABELS.items()}
            all_orders = {}  # (project, ch_key) → orders list

            for i in range(st.session_state[row_count_key]):
                channel_name = st.session_state.get(f"{project_key}_ch_{i}", "").strip()
                sale_month = st.session_state.get(f"{project_key}_month_{i}", "").strip()
                sale_amount = st.session_state.get(f"{project_key}_amt_{i}", 0)

                if not channel_name or not sale_month or sale_amount <= 0:
                    continue

                ch_key = label_to_key.get(channel_name, channel_name.lower().replace(" ", ""))
                if ch_key not in CHANNEL_LABELS:
                    CHANNEL_LABELS[ch_key] = channel_name

                order_date = f"{sale_month}-01"
                order_id = f"manual_{project_key}_{ch_key}_{sale_month}"

                order = {
                    "order_id": order_id,
                    "product_name": f"{channel_name} 수동입력",
                    "quantity": 1,
                    "unit_price": sale_amount,
                    "payment_amount": sale_amount,
                    "order_status": "manual",
                    "order_date": order_date,
                }

                # 같은 채널+월 기존 수동입력 삭제
                with get_conn() as conn:
                    conn.execute("DELETE FROM orders WHERE project=? AND order_id=?", (project_key, order_id))

                if ch_key not in all_orders:
                    all_orders[ch_key] = []
                all_orders[ch_key].append(order)

            if not all_orders:
                st.warning("입력된 데이터가 없습니다.")
                return

            total_saved = 0
            for ch_key, orders in all_orders.items():
                total_saved += save_orders(project_key, ch_key, orders)

            # 행 수 초기화
            st.session_state[row_count_key] = 1
            st.rerun()


def _manual_data_manager(project_key: str):
    """수동 입력/엑셀 업로드 데이터 확인 및 삭제"""
    from app.db import get_conn

    # 수동 입력 데이터 조회 (order_status='manual' 또는 channel='excel')
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT channel, SUBSTR(order_date,1,7) AS month,
                   SUM(payment_amount) AS total, COUNT(*) AS cnt,
                   order_status
            FROM orders
            WHERE project=? AND (order_status='manual' OR channel='excel')
            GROUP BY channel, month
            ORDER BY month DESC, channel
        """, (project_key,)).fetchall()

    if not rows:
        return

    with st.expander("수동 입력 데이터 관리", expanded=False):
        for ch, month, total, cnt, status in rows:
            label = CHANNEL_LABELS.get(ch, ch)
            source = "📝 수동입력" if status == "manual" else "📊 엑셀"
            col_info, col_del = st.columns([5, 1])
            with col_info:
                st.markdown(
                    f'<span style="color:#8b8fa3;font-size:0.85rem;">{source}</span> '
                    f'**{label}** · {month} · ₩{total:,} ({cnt}건)',
                    unsafe_allow_html=True,
                )
            with col_del:
                if st.button("삭제", key=f"del_{project_key}_{ch}_{month}", type="secondary"):
                    with get_conn() as conn:
                        conn.execute("""
                            DELETE FROM orders
                            WHERE project=? AND channel=? AND SUBSTR(order_date,1,7)=?
                              AND (order_status='manual' OR channel='excel')
                        """, (project_key, ch, month))
                    st.rerun()


# ── 전체 대시보드 (프로젝트별 매출) ─────────────────

def show_all_dashboard():
    from app.config import PROJECTS as ALL_PROJECTS

    col_title, col_refresh = st.columns([5, 1])
    with col_title:
        st.title("전체 매출")
    with col_refresh:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("전체 갱신", key="all_refresh", type="secondary", use_container_width=True):
            with st.spinner("전체 매출 데이터 갱신 중 (최근 15일)..."):
                from app.config import get_naver_creds, get_cafe24_creds
                all_results = []
                for pk in ALL_PROJECTS:
                    # API 없는 프로젝트 건너뛰기
                    if not get_naver_creds(pk) and not get_cafe24_creds(pk):
                        continue
                    results = _refresh_project_data(pk)
                    if results:
                        all_results.append(f"[{ALL_PROJECTS[pk]['name']}] {', '.join(results)}")
            if all_results:
                for r in all_results:
                    st.toast(r)
                if _auto_push():
                    st.toast("클라우드 대시보드에 반영 완료!")
            else:
                st.toast("갱신 완료")
            st.rerun()

    data = get_summary(project=None, channel=None)
    proj_summaries = {}
    for pk in ALL_PROJECTS:
        proj_summaries[pk] = get_summary(project=pk, channel=None)

    # 데이터가 있는 프로젝트만
    active_projects = [pk for pk in ALL_PROJECTS if proj_summaries[pk]["year"]["amount"] > 0]

    col1, col2 = st.columns(2)

    with col1:
        year_projs = [
            {"channel": pk, "label": ALL_PROJECTS[pk]["name"], "amount": proj_summaries[pk]["year"]["amount"]}
            for pk in active_projects
        ]
        channel_donut_with_legend(
            year_projs,
            center_label=f"{data['this_year']}년",
            center_amount=data["year"]["amount"],
            key="all_year_donut",
        )
        metric_card(f"{data['this_year']}년 매출", data["year"]["amount"])

    with col2:
        month_projs = [
            {"channel": pk, "label": ALL_PROJECTS[pk]["name"], "amount": proj_summaries[pk]["month"]["amount"]}
            for pk in active_projects
        ]
        channel_donut_with_legend(
            month_projs,
            center_label=data["this_month"],
            center_amount=data["month"]["amount"],
            key="all_month_donut",
        )
        metric_card(f"{data['this_month']} 매출", data["month"]["amount"])

    st.markdown("<br>", unsafe_allow_html=True)
    st.divider()

    st.markdown("#### 일별 추이")
    daily_chart(data, prefix="all")

    st.markdown("#### 월별 추이")
    monthly_chart(data, prefix="all")

    st.caption(f"마지막 수집: {data['last_saved']}")


# ── 메인 ──────────────────────────────────────────

tab_labels = ["📊 전체"] + [info["name"] for info in PROJECTS.values()]
tab_keys = [None] + list(PROJECTS.keys())
tabs = st.tabs(tab_labels)

# 엑셀 업로드 대상 프로젝트 (API 연동 없는 프로젝트)
EXCEL_UPLOAD_PROJECTS = {"lecture"}

for tab, project_key in zip(tabs, tab_keys):
    with tab:
        if project_key is None:
            show_all_dashboard()
        elif project_key == "groupbuy":
            show_project_dashboard(project_key, PROJECTS[project_key]["name"])
        else:
            if project_key in EXCEL_UPLOAD_PROJECTS:
                show_excel_upload(project_key, PROJECTS[project_key]["name"])
            show_project_dashboard(project_key, PROJECTS[project_key]["name"])
