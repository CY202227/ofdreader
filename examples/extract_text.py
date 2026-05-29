#!/usr/bin/env python3
"""Extract text from an OFD file (usage: python extract_text.py path/to/file.ofd)."""

from __future__ import annotations

import sys
from pathlib import Path

from ofdreader import OfdReader


def main() -> int:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <file.ofd>", file=sys.stderr)
        return 1
    path = Path(sys.argv[1])
    reader = OfdReader(path)
    print(f"Pages: {reader.page_count}")
    print(f"Author: {reader.metadata.get('Author', '')}")
    print("---")
    print(reader.extract_text())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
