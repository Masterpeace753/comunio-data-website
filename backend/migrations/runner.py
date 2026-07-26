from __future__ import annotations

from pathlib import Path

from src.config import load_settings
from src.database.connection import connect


def ensure_migration_table(cur) -> None:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            name TEXT PRIMARY KEY,
            applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )


def applied_migrations(cur) -> set[str]:
    cur.execute("SELECT name FROM schema_migrations")
    return {row[0] for row in cur.fetchall()}


def apply_migration(cur, file_path: Path) -> None:
    sql = file_path.read_text(encoding="utf-8")
    cur.execute(sql)
    cur.execute("INSERT INTO schema_migrations(name) VALUES (%s)", (file_path.name,))


def run() -> None:
    settings = load_settings()
    conn = connect(settings.database_url)

    try:
        with conn:
            with conn.cursor() as cur:
                ensure_migration_table(cur)
                done = applied_migrations(cur)

                migration_dir = Path(__file__).resolve().parent
                files = sorted(p for p in migration_dir.glob("*.sql") if p.name[0].isdigit())
                for file_path in files:
                    if file_path.name in done:
                        continue
                    print(f"Applying {file_path.name}")
                    apply_migration(cur, file_path)
    finally:
        conn.close()


if __name__ == "__main__":
    run()
