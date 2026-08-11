from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.svg_golden_cases import GOLDEN_DIR, iter_golden_cases


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate committed SVG golden fixtures.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing fixtures.")
    args = parser.parse_args()

    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    cases = iter_golden_cases()
    existing = [case.fixture_path for case in cases if case.fixture_path.exists()]
    if existing and not args.force:
        existing_names = "\n".join(str(path.relative_to(Path.cwd())) for path in existing)
        raise SystemExit(
            "Golden SVG fixtures already exist. Re-run with --force to overwrite:\n"
            f"{existing_names}"
        )

    for case in cases:
        drawing = case.render()
        case.fixture_path.write_text(drawing.svg, encoding="utf-8")
        print(case.fixture_path.relative_to(Path.cwd()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())