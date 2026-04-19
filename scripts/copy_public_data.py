from __future__ import annotations

import shutil
from pathlib import Path


def main() -> int:
    source = Path("data/sources")
    target = Path("public/data/sources")
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)
    print(f"Copied {source} to {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
