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


# Inicializa ao importar
init_db()
