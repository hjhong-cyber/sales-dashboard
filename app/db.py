"""SQLite DB - 멀티 프로젝트 × 멀티 채널 통합"""
import sqlite3
from datetime import datetime

DB_PATH = "orders.db"


def get_conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                project          TEXT NOT NULL,
                channel          TEXT NOT NULL,
                order_id         TEXT NOT NULL,
                product_name     TEXT,
                quantity         INTEGER,
                unit_price       INTEGER,
                payment_amount   INTEGER,
                order_status     TEXT,
                order_date       TEXT,
                saved_at         TEXT,
                UNIQUE(project, channel, order_id)
            )
        """)
        # 인덱스: 날짜 기반 집계 성능
        conn.execute("CREATE INDEX IF NOT EXISTS idx_order_date ON orders(order_date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_project_channel ON orders(project, channel)")
    print("[OK] DB 초기화 완료")


def save_orders(project: str, channel: str, orders: list[dict]) -> int:
    if not orders:
        return 0
    saved_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows = [
        (
            project,
            channel,
            o["order_id"],
            o.get("product_name", ""),
            o.get("quantity", 0),
            o.get("unit_price", 0),
            o.get("payment_amount", 0),
            o.get("order_status", ""),
            o.get("order_date", ""),
            saved_at,
        )
        for o in orders
        if o.get("order_id")
    ]
    with get_conn() as conn:
        cursor = conn.executemany("""
            INSERT OR IGNORE INTO orders
            (project, channel, order_id, product_name, quantity, unit_price,
             payment_amount, order_status, order_date, saved_at)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, rows)
    return cursor.rowcount
