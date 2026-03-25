"""SQLite database — persistência local."""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "ml_dashboard.db"


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Cria tabelas se não existirem."""
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS competitors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nickname TEXT,
                seller_id TEXT,
                name TEXT,
                notes TEXT DEFAULT '',
                active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                item_id TEXT,
                catalog_product_id TEXT,
                title TEXT,
                price REAL,
                seller_id TEXT,
                seller_nickname TEXT,
                brand TEXT,
                model TEXT,
                status TEXT,
                captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_price_history_query
            ON price_history(query, captured_at)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_price_history_product
            ON price_history(catalog_product_id, captured_at)
        """)
        conn.commit()


# ── CRUD Concorrentes ─────────────────────────────────

def get_competitors(active_only: bool = True) -> list[dict]:
    with _conn() as conn:
        if active_only:
            rows = conn.execute(
                "SELECT * FROM competitors WHERE active = 1 ORDER BY name"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM competitors ORDER BY active DESC, name"
            ).fetchall()
        return [dict(r) for r in rows]


def get_competitor(comp_id: int) -> dict | None:
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM competitors WHERE id = ?", (comp_id,)
        ).fetchone()
        return dict(row) if row else None


def create_competitor(nickname: str = "", seller_id: str = "",
                      name: str = "", notes: str = "") -> int:
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO competitors (nickname, seller_id, name, notes) VALUES (?, ?, ?, ?)",
            (nickname.strip(), seller_id.strip(), name.strip(), notes.strip()),
        )
        conn.commit()
        return cur.lastrowid


def update_competitor(comp_id: int, **fields) -> bool:
    allowed = {"nickname", "seller_id", "name", "notes", "active"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return False
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [comp_id]
    with _conn() as conn:
        conn.execute(
            f"UPDATE competitors SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            values,
        )
        conn.commit()
    return True


def delete_competitor(comp_id: int) -> bool:
    with _conn() as conn:
        conn.execute("DELETE FROM competitors WHERE id = ?", (comp_id,))
        conn.commit()
    return True


# ── Histórico de Preços ───────────────────────────────

def save_search_results(query: str, results: list):
    """Salva resultados de busca no histórico de preços."""
    if not results:
        return
    with _conn() as conn:
        for r in results:
            conn.execute("""
                INSERT INTO price_history
                (query, item_id, catalog_product_id, title, price, seller_id,
                 seller_nickname, brand, model, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                query.strip().lower(),
                r.get("id", ""),
                r.get("catalog_product_id", ""),
                r.get("title", ""),
                r.get("price", 0),
                str(r.get("seller", {}).get("id", "")),
                r.get("seller", {}).get("nickname", ""),
                r.get("brand", ""),
                r.get("model", ""),
                r.get("status", ""),
            ))
        conn.commit()


def get_price_history(query: str = "", product_id: str = "",
                      days: int = 90) -> list[dict]:
    """Retorna histórico de preços filtrado."""
    with _conn() as conn:
        if product_id:
            rows = conn.execute("""
                SELECT * FROM price_history
                WHERE catalog_product_id = ?
                AND captured_at >= datetime('now', ?)
                ORDER BY captured_at
            """, (product_id, f"-{days} days")).fetchall()
        elif query:
            rows = conn.execute("""
                SELECT * FROM price_history
                WHERE query = ?
                AND captured_at >= datetime('now', ?)
                ORDER BY captured_at
            """, (query.strip().lower(), f"-{days} days")).fetchall()
        else:
            rows = conn.execute("""
                SELECT * FROM price_history
                WHERE captured_at >= datetime('now', ?)
                ORDER BY captured_at DESC
                LIMIT 1000
            """, (f"-{days} days",)).fetchall()
        return [dict(r) for r in rows]


def get_tracked_queries() -> list[str]:
    """Retorna lista de queries já buscadas (para dropdown)."""
    with _conn() as conn:
        rows = conn.execute("""
            SELECT DISTINCT query FROM price_history ORDER BY query
        """).fetchall()
        return [r["query"] for r in rows]


def get_price_summary(query: str, days: int = 90) -> list[dict]:
    """Retorna preço médio/min/max por dia para uma query."""
    with _conn() as conn:
        rows = conn.execute("""
            SELECT
                date(captured_at) as date,
                COUNT(*) as count,
                AVG(price) as avg_price,
                MIN(price) as min_price,
                MAX(price) as max_price
            FROM price_history
            WHERE query = ? AND price > 0
            AND captured_at >= datetime('now', ?)
            GROUP BY date(captured_at)
            ORDER BY date
        """, (query.strip().lower(), f"-{days} days")).fetchall()
        return [dict(r) for r in rows]


# Inicializa ao importar
init_db()
