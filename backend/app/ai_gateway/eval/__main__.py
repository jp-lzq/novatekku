"""python -m app.ai_gateway.eval [--json]  — print the understanding benchmark."""

import json
import sys

from .runner import format_report, run


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    score = run()
    if "--json" in args:
        print(json.dumps(score.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(format_report(score))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
