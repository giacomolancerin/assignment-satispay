"""Entry point: `python -m blog_automation`."""

from __future__ import annotations

import sys
from datetime import date

from .graph import build_graph
from .state import PipelineState


def main(run_date: str | None = None) -> int:
    if run_date is None:
        run_date = date.today().isoformat()

    print(f"=== Blog automation pipeline — run {run_date} ===")
    graph = build_graph()
    initial: PipelineState = {"run_date": run_date}
    final = graph.invoke(initial)

    published = final.get("published", [])
    errors = final.get("errors", [])
    print(f"\n=== Done. Published: {len(published)}. Errors: {len(errors)}. ===")
    for e in errors:
        print(f"  ! [{e.node}] {e.article_slug or '-'}: {e.message}")

    return 0 if published else 1


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    sys.exit(main(arg))
