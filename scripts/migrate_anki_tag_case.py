from __future__ import annotations

import argparse
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from shutil import copy2
from typing import Iterable


TAG_CASE_MAP = {
    "custom": "CUSTOM",
    "added-2026": "ADDED-2026",
    "hsk1": "HSK1",
    "hsk2": "HSK2",
    "hsk3": "HSK3",
    "hsk4": "HSK4",
}


@dataclass
class MigrationCounts:
    notes_updated: int = 0
    tag_rows_updated: int = 0


def register_unicase(connection: sqlite3.Connection) -> None:
    connection.create_collation(
        "unicase",
        lambda left, right: (left.casefold() > right.casefold()) - (left.casefold() < right.casefold()),
    )


def normalize_note_tags(note_tags: str, replacements: dict[str, str]) -> str:
    normalized = note_tags
    for old, new in replacements.items():
        normalized = normalized.replace(f" {old} ", f" {new} ")
    return normalized


def timestamp_suffix() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


def backup_collection(collection_path: Path, backup_dir: Path) -> list[Path]:
    backup_dir.mkdir(parents=True, exist_ok=True)
    backups: list[Path] = []
    for source in collection_sidecars(collection_path):
        destination = backup_dir / f"{source.name}.{timestamp_suffix()}.bak"
        copy2(source, destination)
        backups.append(destination)
    return backups


def collection_sidecars(collection_path: Path) -> Iterable[Path]:
    yield collection_path
    for suffix in ("-wal", "-shm"):
        sidecar = Path(f"{collection_path}{suffix}")
        if sidecar.exists():
            yield sidecar


def note_counts(connection: sqlite3.Connection, tags: Iterable[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for tag in tags:
        count = connection.execute(
            "select count(*) from notes where instr(tags, ?) > 0",
            (f" {tag} ",),
        ).fetchone()[0]
        counts[tag] = int(count)
    return counts


def tag_table_values(connection: sqlite3.Connection) -> list[str]:
    rows = connection.execute(
        "select tag from tags where lower(tag) in ({}) order by lower(tag)".format(
            ",".join("?" for _ in TAG_CASE_MAP),
        ),
        tuple(TAG_CASE_MAP),
    ).fetchall()
    return [str(row[0]) for row in rows]


def migrate_connection(connection: sqlite3.Connection, replacements: dict[str, str]) -> MigrationCounts:
    counts = MigrationCounts()
    now_seconds = int(time.time())
    now_millis = now_seconds * 1000

    for old, new in replacements.items():
        cursor = connection.execute(
            """
            update notes
               set tags = replace(tags, ?, ?),
                   mod = ?,
                   usn = -1
             where instr(tags, ?) > 0
            """,
            (f" {old} ", f" {new} ", now_seconds, f" {old} "),
        )
        counts.notes_updated += int(cursor.rowcount)

        temp = f"__TMP_{new}__"
        connection.execute(
            "update tags set tag = ?, usn = -1 where lower(tag) = ? and tag != ?",
            (temp, old, temp),
        )
        cursor = connection.execute(
            "update tags set tag = ?, usn = -1 where tag = ?",
            (new, temp),
        )
        counts.tag_rows_updated += int(cursor.rowcount)

    connection.execute("update col set mod = ?", (now_millis,))
    return counts


def verify_migration(connection: sqlite3.Connection, replacements: dict[str, str]) -> None:
    lowercase_counts = note_counts(connection, replacements)
    remaining = {tag: count for tag, count in lowercase_counts.items() if count}
    if remaining:
        raise RuntimeError(f"Lowercase tags still present in notes: {remaining}")

    table_tags = {tag.casefold(): tag for tag in tag_table_values(connection)}
    missing = [new for new in replacements.values() if table_tags.get(new.casefold()) != new]
    if missing:
        raise RuntimeError(f"Uppercase tags missing from tags table: {missing}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Uppercase legacy generated tags in a closed Anki collection.")
    parser.add_argument(
        "--collection",
        type=Path,
        default=Path.home() / "Library/Application Support/Anki2/User 1/collection.anki2",
    )
    parser.add_argument("--backup-dir", type=Path, default=Path("logs/anki-backups"))
    parser.add_argument("--no-backup", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.collection.exists():
        raise SystemExit(f"Collection not found: {args.collection}")

    backups: list[Path] = []
    if not args.no_backup:
        backups = backup_collection(args.collection, args.backup_dir)

    connection = sqlite3.connect(args.collection)
    try:
        register_unicase(connection)
        connection.execute("begin immediate")
        counts = migrate_connection(connection, TAG_CASE_MAP)
        verify_migration(connection, TAG_CASE_MAP)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    print(
        "Anki tag case migration complete:",
        {
            "notes_updated": counts.notes_updated,
            "tag_rows_updated": counts.tag_rows_updated,
            "backups": [str(path) for path in backups],
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
