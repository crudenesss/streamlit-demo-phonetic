import json
import sqlite3
from pathlib import Path

DB_PATH = Path("words.db")
JSON_PATH = Path("words.json")


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS groups (
            id           INTEGER PRIMARY KEY,
            name         TEXT NOT NULL UNIQUE,
            source_photo TEXT
        );
        CREATE TABLE IF NOT EXISTS words (
            id           INTEGER PRIMARY KEY,
            word         TEXT NOT NULL,
            transcription TEXT NOT NULL,
            group_id     INTEGER NOT NULL REFERENCES groups(id),
            UNIQUE(word)
        );
    """)
    conn.commit()


def upsert(conn: sqlite3.Connection, groups: list[dict]) -> tuple[int, int, int, int]:
    g_new = g_skipped = w_inserted = w_updated = 0
    for group in groups:
        cur = conn.execute(
            "INSERT INTO groups (name) VALUES (?) ON CONFLICT(name) DO NOTHING",
            (group["name"],),
        )
        if cur.rowcount:
            g_new += 1
        else:
            g_skipped += 1

        (group_id,) = conn.execute(
            "SELECT id FROM groups WHERE name = ?", (group["name"],)
        ).fetchone()

        for entry in group.get("entries", []):
            existing = conn.execute(
                "SELECT transcription, group_id FROM words WHERE word = ?",
                (entry["word"],),
            ).fetchone()
            conn.execute(
                """
                INSERT INTO words (word, transcription, group_id) VALUES (?, ?, ?)
                ON CONFLICT(word) DO UPDATE SET
                    transcription = excluded.transcription,
                    group_id      = excluded.group_id
                """,
                (entry["word"], entry["transcription"], group_id),
            )
            if existing is None:
                w_inserted += 1
            else:
                w_updated += 1

    conn.commit()
    return g_new, g_skipped, w_inserted, w_updated


def main() -> None:
    if not JSON_PATH.exists():
        print(f"Not found: {JSON_PATH}")
        raise SystemExit(1)

    data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    groups = data["groups"]

    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    g_new, g_skipped, w_inserted, w_updated = upsert(conn, groups)
    conn.close()

    print(
        f"Groups : {g_new} inserted, {g_skipped} already existed\n"
        f"Words  : {w_inserted} inserted, {w_updated} updated\n"
        f"DB     : {DB_PATH}"
    )


if __name__ == "__main__":
    main()
