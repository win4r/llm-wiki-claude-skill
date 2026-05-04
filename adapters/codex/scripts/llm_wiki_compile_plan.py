#!/usr/bin/env python3
"""Generate a deterministic compile plan for oversized/index-drift llm-wikis."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


CONTENT_DIRS = ("entities", "concepts", "comparisons", "queries")
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?", re.S)


def default_wiki_path() -> Path:
    raw = os.environ.get("LLM_WIKI_PATH") or os.environ.get("WIKI_PATH")
    if raw:
        return Path(raw).expanduser()
    return Path.home() / "wiki" / "llm-wiki"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plan llm-wiki compile work")
    parser.add_argument("--wiki", type=Path, default=default_wiki_path())
    parser.add_argument("--max-words", type=int, default=1200)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def content_pages(wiki: Path) -> list[Path]:
    pages: list[Path] = []
    for directory in CONTENT_DIRS:
        root = wiki / directory
        if root.exists():
            pages.extend(sorted(path for path in root.rglob("*.md") if path.is_file()))
    return pages


def word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", FRONTMATTER_RE.sub("", text, count=1)))


def title_key(path: Path) -> str:
    return re.sub(r"[^a-z0-9]+", "-", path.stem.lower()).strip("-")


def build_plan(wiki: Path, max_words: int) -> dict[str, Any]:
    wiki = wiki.expanduser().resolve()
    index_text = (wiki / "index.md").read_text(encoding="utf-8") if (wiki / "index.md").exists() else ""
    oversized: list[dict[str, Any]] = []
    not_indexed: list[str] = []
    by_key: dict[str, list[str]] = defaultdict(list)

    for path in content_pages(wiki):
        rel = path.relative_to(wiki).as_posix()
        text = path.read_text(encoding="utf-8")
        words = word_count(text)
        if words > max_words:
            rel_stem = Path(rel).with_suffix("").as_posix()
            oversized.append(
                {
                    "path": rel,
                    "words": words,
                    "suggestion": f"split into {rel_stem}/index.md plus focused aspect pages",
                }
            )
        if f"[[{path.stem}" not in index_text and f"[[{path.relative_to(wiki).with_suffix('').as_posix()}" not in index_text:
            not_indexed.append(rel)
        by_key[title_key(path)].append(rel)

    duplicates = [
        {"key": key, "pages": pages}
        for key, pages in sorted(by_key.items())
        if len(pages) > 1
    ]
    return {
        "wiki": str(wiki),
        "max_words": max_words,
        "oversized_pages": oversized,
        "not_indexed": not_indexed,
        "near_duplicates": duplicates,
        "needs_compile": bool(oversized or not_indexed or duplicates),
    }


def main() -> int:
    args = parse_args()
    plan = build_plan(args.wiki, args.max_words)
    if args.json:
        print(json.dumps(plan, indent=2, sort_keys=True))
    else:
        print(f"Wiki: {plan['wiki']}")
        print(f"Needs compile: {plan['needs_compile']}")
        for key in ("oversized_pages", "not_indexed", "near_duplicates"):
            print(f"\n## {key} ({len(plan[key])})")
            for item in plan[key]:
                print(f"- {item}")
    return 1 if plan["needs_compile"] else 0


if __name__ == "__main__":
    sys.exit(main())
