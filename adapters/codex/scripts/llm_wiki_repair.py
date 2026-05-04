#!/usr/bin/env python3
"""Repair common llm-wiki schema drift in a non-destructive, dry-run-first way."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
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
    parser = argparse.ArgumentParser(description="Repair common llm-wiki frontmatter drift")
    parser.add_argument("--wiki", type=Path, default=default_wiki_path())
    parser.add_argument("--apply", action="store_true", help="Write repairs. Default is dry-run.")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def content_pages(wiki: Path) -> list[Path]:
    pages: list[Path] = []
    for directory in CONTENT_DIRS:
        root = wiki / directory
        if root.exists():
            pages.extend(sorted(path for path in root.rglob("*.md") if path.is_file()))
    return pages


def has_nonempty_sources(frontmatter: str) -> bool:
    match = re.search(r"^sources:\s*(.*)$", frontmatter, re.M)
    if not match:
        return False
    value = match.group(1).strip()
    if value and value not in ("[]", "null", "None"):
        return True
    following = frontmatter[match.end() :].splitlines()
    return any(line.startswith("  - ") for line in following)


def repair_frontmatter(wiki: Path, path: Path, text: str) -> tuple[str, list[str]]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return text, []
    frontmatter = match.group(1)
    actions: list[str] = []

    if re.search(r"^type:\s*paper\s*$", frontmatter, re.M):
        frontmatter = re.sub(r"^type:\s*paper\s*$", "type: summary", frontmatter, flags=re.M)
        actions.append("type: paper -> summary")

    if not has_nonempty_sources(frontmatter):
        rel = path.relative_to(wiki).with_suffix("").as_posix().replace("/", "-")
        ref_rel = f"raw/refs/{rel}-source-needed.md"
        if re.search(r"^sources:\s*.*$", frontmatter, re.M):
            frontmatter = re.sub(r"^sources:\s*.*$", f"sources: [{ref_rel}]", frontmatter, flags=re.M)
        else:
            frontmatter += f"\nsources: [{ref_rel}]"
        actions.append(f"add placeholder source {ref_rel}")

    if not actions:
        return text, []
    repaired = f"---\n{frontmatter}\n---\n" + text[match.end() :]
    return repaired, actions


def placeholder_text(ref_rel: str, page_rel: str) -> str:
    return f"""---
kind: ref
status: source-needed
---

Placeholder source pointer for [[{page_rel.removesuffix('.md')}]].
Replace this with the original raw source when available.
"""


def repair(wiki: Path, apply: bool) -> dict[str, Any]:
    wiki = wiki.expanduser().resolve()
    changes: list[dict[str, Any]] = []
    for path in content_pages(wiki):
        text = path.read_text(encoding="utf-8")
        repaired, actions = repair_frontmatter(wiki, path, text)
        if not actions:
            continue
        rel = path.relative_to(wiki).as_posix()
        change: dict[str, Any] = {"path": rel, "actions": actions}
        ref_paths = [
            action.rsplit(" ", 1)[-1]
            for action in actions
            if action.startswith("add placeholder source ")
        ]
        if ref_paths:
            change["placeholder_sources"] = ref_paths
        changes.append(change)
        if apply:
            path.write_text(repaired, encoding="utf-8")
            for ref_rel in ref_paths:
                ref_path = wiki / ref_rel
                ref_path.parent.mkdir(parents=True, exist_ok=True)
                if not ref_path.exists():
                    ref_path.write_text(placeholder_text(ref_rel, rel), encoding="utf-8")
    return {"wiki": str(wiki), "mode": "apply" if apply else "dry-run", "changes": changes}


def main() -> int:
    args = parse_args()
    report = repair(args.wiki, args.apply)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"Wiki: {report['wiki']}")
        print(f"Mode: {report['mode']}")
        for change in report["changes"]:
            print(f"- {change['path']}: {', '.join(change['actions'])}")
        if not report["changes"]:
            print("No repairs needed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
