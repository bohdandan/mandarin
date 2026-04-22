from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
import time
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.chinese_support import updated_chinese_advanced_css, with_written_chinese_footer


def read_varint(data: bytes, offset: int) -> tuple[int, int]:
    value = 0
    shift = 0
    while True:
        byte = data[offset]
        offset += 1
        value |= (byte & 0x7F) << shift
        if not (byte & 0x80):
            return value, offset
        shift += 7


def write_varint(value: int) -> bytes:
    encoded = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            encoded.append(byte | 0x80)
        else:
            encoded.append(byte)
            return bytes(encoded)


def decode_template_config(blob: bytes) -> tuple[str, str, list[tuple[int, int, bytes | int]]]:
    offset = 0
    qfmt = ""
    afmt = ""
    extra: list[tuple[int, int, bytes | int]] = []
    while offset < len(blob):
        key, offset = read_varint(blob, offset)
        field_number = key >> 3
        wire_type = key & 0x07
        if wire_type == 2:
            length, offset = read_varint(blob, offset)
            value = blob[offset : offset + length]
            offset += length
            if field_number == 1:
                qfmt = value.decode("utf-8")
            elif field_number == 2:
                afmt = value.decode("utf-8")
            else:
                extra.append((field_number, wire_type, value))
        elif wire_type == 0:
            value, offset = read_varint(blob, offset)
            extra.append((field_number, wire_type, value))
        else:
            raise RuntimeError(f"Unsupported wire type {wire_type} in template config")
    return qfmt, afmt, extra


def encode_template_config(qfmt: str, afmt: str, extra: list[tuple[int, int, bytes | int]] | None = None) -> bytes:
    parts = [
        write_varint((1 << 3) | 2),
        write_varint(len(qfmt.encode("utf-8"))),
        qfmt.encode("utf-8"),
        write_varint((2 << 3) | 2),
        write_varint(len(afmt.encode("utf-8"))),
        afmt.encode("utf-8"),
    ]
    for field_number, wire_type, value in extra or []:
        parts.append(write_varint((field_number << 3) | wire_type))
        if wire_type == 2:
            raw = value if isinstance(value, bytes) else bytes(value)
            parts.append(write_varint(len(raw)))
            parts.append(raw)
        elif wire_type == 0:
            parts.append(write_varint(int(value)))
        else:
            raise RuntimeError(f"Unsupported wire type {wire_type} in template config")
    return b"".join(parts)


def decode_notetype_config(blob: bytes) -> tuple[str, list[tuple[int, int, bytes | int]]]:
    offset = 0
    css = ""
    extra: list[tuple[int, int, bytes | int]] = []
    while offset < len(blob):
        key, offset = read_varint(blob, offset)
        field_number = key >> 3
        wire_type = key & 0x07
        if wire_type == 2:
            length, offset = read_varint(blob, offset)
            value = blob[offset : offset + length]
            offset += length
            if field_number == 3:
                css = value.decode("utf-8")
            else:
                extra.append((field_number, wire_type, value))
        elif wire_type == 0:
            value, offset = read_varint(blob, offset)
            extra.append((field_number, wire_type, value))
        else:
            raise RuntimeError(f"Unsupported wire type {wire_type} in notetype config")
    return css, extra


def encode_notetype_config(css: str, extra: list[tuple[int, int, bytes | int]] | None = None) -> bytes:
    parts = [
        write_varint((3 << 3) | 2),
        write_varint(len(css.encode("utf-8"))),
        css.encode("utf-8"),
    ]
    for field_number, wire_type, value in extra or []:
        parts.append(write_varint((field_number << 3) | wire_type))
        if wire_type == 2:
            raw = value if isinstance(value, bytes) else bytes(value)
            parts.append(write_varint(len(raw)))
            parts.append(raw)
        elif wire_type == 0:
            parts.append(write_varint(int(value)))
        else:
            raise RuntimeError(f"Unsupported wire type {wire_type} in notetype config")
    return b"".join(parts)


def update_back_template(blob: bytes, back_template: str) -> bytes:
    qfmt, _, extra = decode_template_config(blob)
    return encode_template_config(qfmt, back_template, extra)


def update_notetype_css(blob: bytes, css: str) -> bytes:
    _, extra = decode_notetype_config(blob)
    return encode_notetype_config(css, extra)


def backup_collection(collection_path: Path, backup_dir: Path) -> list[Path]:
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    backups: list[Path] = []
    for source in (collection_path, Path(f"{collection_path}-wal"), Path(f"{collection_path}-shm")):
        if source.exists():
            target = backup_dir / f"{source.name}.{stamp}.bak"
            shutil.copy2(source, target)
            backups.append(target)
    return backups


def update_collection_template(collection_path: Path, backup_dir: Path) -> tuple[int, int, list[Path]]:
    backups = backup_collection(collection_path, backup_dir)
    conn = sqlite3.connect(collection_path)
    conn.create_collation("unicase", lambda a, b: (a.casefold() > b.casefold()) - (a.casefold() < b.casefold()))
    try:
        template_row = conn.execute(
            """
            select t.ntid, t.ord, t.config
            from templates t
            join notetypes n on n.id = t.ntid
            where n.name = 'Chinese (Advanced)'
            order by t.ord
            limit 1
            """
        ).fetchone()
        if template_row is None:
            raise RuntimeError("Chinese (Advanced) template not found in collection.")
        ntid, ord_, template_blob = template_row
        _, afmt, _ = decode_template_config(template_blob)
        updated_afmt = with_written_chinese_footer(afmt)

        notetype_row = conn.execute("select config from notetypes where id = ?", (ntid,)).fetchone()
        if notetype_row is None:
            raise RuntimeError("Chinese (Advanced) note type config not found in collection.")
        notetype_blob = notetype_row[0]
        css, _ = decode_notetype_config(notetype_blob)
        updated_css = updated_chinese_advanced_css(css)

        now_seconds = int(time.time())
        updated_templates = 0
        updated_notetypes = 0
        if updated_afmt != afmt:
            updated_blob = update_back_template(template_blob, updated_afmt)
            conn.execute(
                "update templates set config = ?, mtime_secs = ?, usn = -1 where ntid = ? and ord = ?",
                (updated_blob, now_seconds, ntid, ord_),
            )
            updated_templates = 1
        if updated_css != css:
            updated_notetype_blob = update_notetype_css(notetype_blob, updated_css)
            conn.execute(
                "update notetypes set config = ?, mtime_secs = ?, usn = -1 where id = ?",
                (updated_notetype_blob, now_seconds, ntid),
            )
            updated_notetypes = 1
        if not updated_templates and not updated_notetypes:
            return 0, 0, backups
        conn.execute("update col set mod = ?", (now_seconds * 1000,))
        conn.commit()
        return updated_templates, updated_notetypes, backups
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Append the Written Chinese footer link to the Chinese (Advanced) back template.")
    parser.add_argument(
        "--collection",
        type=Path,
        default=Path.home() / "Library/Application Support/Anki2/User 1/collection.anki2",
    )
    parser.add_argument("--backup-dir", type=Path, default=Path("logs/anki-backups"))
    args = parser.parse_args()

    updated_templates, updated_notetypes, backups = update_collection_template(args.collection, args.backup_dir)
    print(
        {
            "updated_templates": updated_templates,
            "updated_notetypes": updated_notetypes,
            "backups": [str(path) for path in backups],
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
