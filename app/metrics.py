"""DB 집계 - 멀티 프로젝트 × 멀티 채널"""
from datetime import date
from app.db import get_conn

CHANNEL_LABELS = {
    "naver":          "네이버",
    "cafe24":         "자사몰",
    "coupang":        "쿠팡",
    "shopify":        "Shopify",
    "cjonstyle":      "CJ온스타일",
    "cafe24_youtube": "유튜브쇼핑",
    "zvzo":           "ZVZO",
    "shinsegae":      "신세계몰",
    "gsshop":         "GS SHOP",
    "kurly":          "컬리",
    "lotteon":        "롯데온",
    "kakao":          "카카오",
    "woorisiktuk":    "우리의식탁",
    "toss":           "토스쇼핑",
    "wellstory":      "웰스토리",
    "shinsegaetv":    "신세계TV",
    "11st":           "11번가",
    "gmarket":        "지마켓",
    "auction":        "옥션",
    "excel":          "엑셀",
    "mango_total":    "더망고",
}


def _period_metrics(conn, where: str, params: tuple) -> dict:
    row = conn.execute(
        f"SELECT COUNT(*), COALESCE(SUM(payment_amount),0) FROM orders WHERE {where}", params
    ).fetchone()
    return {"count": row[0], "amount": row[1]}


def get_available_months(project: str | None = None) -> list[str]:
    """DB에 있는 월 목록을 최신순으로 반환"""
    filters = []
    params = ()
    if project:
        filters.append("project = ?")
        params = (project,)
    base = " AND ".join(filters) if filters else "1=1"
    with get_conn() as conn:
        rows = conn.execute(f"""
            SELECT DISTINCT SUBSTR(order_date,1,7) AS month
            FROM orders WHERE ({base}) AND order_date != ''
            ORDER BY month DESC
        """, params).fetchall()
    return [r[0] for r in rows]


def get_summary(project: str | None = None, channel: str | None = None,
                target_month: str | None = None) -> dict:
    """
    project=None  → 전체 회사 합산
    project='glener' → 해당 프로젝트만
    channel=None  → 전체 채널 합산
    channel='naver' → 해당 채널만
    target_month='2026-03' → 특정 월 데이터 조회 (None이면 당월)
    """
    today      = date.today().isoformat()
    this_year  = today[:4]
    this_month = target_month or today[:7]

    filters = []
    params_base = ()

    if project:
        filters.append("project = ?")
        params_base += (project,)
    if channel:
        filters.append("channel = ?")
        params_base += (channel,)

    base_filter = " AND ".join(filters) if filters else "1=1"

    with get_conn() as conn:
        def q(extra_where, extra_params=()):
            where  = f"({base_filter}) AND ({extra_where})"
            params = params_base + extra_params
            return _period_metrics(conn, where, params)

        today_m  = q("SUBSTR(order_date,1,10) = ?", (today,))
        year_m   = q("SUBSTR(order_date,1,4)  = ?", (this_year,))
        month_m  = q("SUBSTR(order_date,1,7)  = ?", (this_month,))

        # 채널별 당월 매출
        channel_rows = conn.execute(f"""
            SELECT channel, COUNT(*), COALESCE(SUM(payment_amount),0)
            FROM orders
            WHERE ({base_filter}) AND SUBSTR(order_date,1,7) = ?
            GROUP BY channel
        """, params_base + (this_month,)).fetchall()

        # 일별
        daily_rows = conn.execute(f"""
            SELECT SUBSTR(order_date,1,10) AS day,
                   COUNT(*), COALESCE(SUM(payment_amount),0)
            FROM orders
            WHERE ({base_filter}) AND order_date != ''
            GROUP BY day ORDER BY day ASC
        """, params_base).fetchall()

        # 월별
        monthly_rows = conn.execute(f"""
            SELECT SUBSTR(order_date,1,7) AS month,
                   COUNT(*), COALESCE(SUM(payment_amount),0)
            FROM orders
            WHERE ({base_filter}) AND order_date != ''
            GROUP BY month ORDER BY month ASC
        """, params_base).fetchall()

        # 연간
        yearly_rows = conn.execute(f"""
            SELECT SUBSTR(order_date,1,4) AS year,
                   COUNT(*), COALESCE(SUM(payment_amount),0)
            FROM orders
            WHERE ({base_filter}) AND order_date != ''
            GROUP BY year ORDER BY year ASC
        """, params_base).fetchall()

        # 전체 누적 매출
        total_row = conn.execute(f"""
            SELECT COUNT(*), COALESCE(SUM(payment_amount),0)
            FROM orders WHERE {base_filter}
        """, params_base).fetchone()

        last_saved = conn.execute(f"""
            SELECT MAX(saved_at) FROM orders WHERE {base_filter}
        """, params_base).fetchone()[0] or "-"

    return {
        "today":      today_m,
        "year":       year_m,
        "month":      month_m,
        "total":      {"count": total_row[0], "amount": total_row[1]},
        "this_year":  this_year,
        "this_month": this_month,
        "last_saved": last_saved,
        "channels": [
            {
                "channel": r[0],
                "label":   CHANNEL_LABELS.get(r[0], r[0]),
                "count":   r[1],
                "amount":  r[2],
            }
            for r in channel_rows
        ],
        "daily":   [{"day":   r[0], "count": r[1], "amount": r[2]} for r in daily_rows],
        "monthly": [{"month": r[0], "count": r[1], "amount": r[2]} for r in monthly_rows],
        "yearly":  [{"year":  r[0], "count": r[1], "amount": r[2]} for r in yearly_rows],
    }


def get_all_projects_summary() -> dict:
    """전체 프로젝트 목록과 각 프로젝트의 당월 매출 반환"""
    this_month = date.today().isoformat()[:7]
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT project, COUNT(*), COALESCE(SUM(payment_amount),0)
            FROM orders
            WHERE SUBSTR(order_date,1,7) = ?
            GROUP BY project
        """, (this_month,)).fetchall()
    return {r[0]: {"count": r[1], "amount": r[2]} for r in rows}


def get_project_channels(project: str) -> list[str]:
    """프로젝트에 데이터가 있는 채널 목록 반환"""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT channel FROM orders WHERE project = ? ORDER BY channel",
            (project,)
        ).fetchall()
    return [r[0] for r in rows]
