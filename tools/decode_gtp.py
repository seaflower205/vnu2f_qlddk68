#!/usr/bin/env python3
"""Decode gCadas .gtp files that are XOR-obfuscated SQLite databases.

Observed on DC2.gtp:
- file length is a multiple of 4096 bytes;
- one encrypted 4096-byte page is repeated many times;
- that repeated page represents an empty SQLite leaf table page;
- decoded output passes SQLite integrity_check.
"""

from __future__ import annotations

import argparse
import sqlite3
from collections import Counter
from pathlib import Path


PAGE_SIZE = 4096


def decode_gtp(input_path: Path, output_path: Path) -> None:
    data = input_path.read_bytes()
    if len(data) % PAGE_SIZE != 0:
        raise ValueError(f"File size {len(data)} is not a multiple of {PAGE_SIZE}")

    pages = [data[i : i + PAGE_SIZE] for i in range(0, len(data), PAGE_SIZE)]
    mask_page, mask_count = Counter(pages).most_common(1)[0]
    if mask_count < 2:
        raise ValueError("No repeated page found; this does not match the observed gCadas GTP pattern")

    empty_sqlite_leaf = bytearray(PAGE_SIZE)
    empty_sqlite_leaf[0] = 0x0D
    empty_sqlite_leaf[5] = 0x10

    decoded = bytearray()
    for page in pages:
        decoded.extend(a ^ b ^ c for a, b, c in zip(page, mask_page, empty_sqlite_leaf))

    if not decoded.startswith(b"SQLite format 3\x00"):
        raise ValueError("Decoded file does not start with a SQLite header")

    output_path.write_bytes(decoded)


def inspect_sqlite(path: Path) -> None:
    con = sqlite3.connect(path)
    cur = con.cursor()
    integrity = cur.execute("PRAGMA integrity_check").fetchone()[0]
    print(f"integrity_check: {integrity}")

    tables = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    non_empty: list[tuple[str, int]] = []
    for (name,) in tables:
        count = cur.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
        if count:
            non_empty.append((name, count))

    print("non-empty tables:")
    for name, count in non_empty:
        print(f"  {name}: {count}")
    con.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Decode a gCadas .gtp file to SQLite")
    parser.add_argument("input", type=Path, help="Input .gtp path")
    parser.add_argument("output", type=Path, help="Output .sqlite path")
    parser.add_argument("--inspect", action="store_true", help="Run basic SQLite inspection after decoding")
    args = parser.parse_args()

    decode_gtp(args.input, args.output)
    print(f"decoded: {args.output}")
    if args.inspect:
        inspect_sqlite(args.output)


if __name__ == "__main__":
    main()
