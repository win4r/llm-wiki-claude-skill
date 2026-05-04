#!/usr/bin/env python3
"""Check that llm-wiki adapters preserve the core workflow semantics."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT_REQUIREMENTS = {
    "boundary": ["Boundary", "Memory"],
    "orientation": ["Orient Before Acting", "SCHEMA.md", "index.md", "log"],
    "operations": ["Ingest", "Query", "Lint", "Compile"],
    "raw_immutable": ["Raw sources", "immutable"],
    "frontmatter": ["title:", "created:", "updated:", "type:", "tags:", "sources:"],
}

ADAPTER_REQUIREMENTS = {
    "adapters/codex/SKILL.md": ["exec_command", "apply_patch", "llm_wiki_lint.py", "llm_wiki_scaffold.py", "$WIKI"],
    "adapters/hermes/SKILL.md": ["read_file", "write_file", "apply_patch", "search_files", "WIKI_PATH"],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check adapter parity")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def missing_terms(text: str, terms: list[str]) -> list[str]:
    lowered = text.lower()
    return [term for term in terms if term.lower() not in lowered]


def check(root: Path) -> dict[str, Any]:
    root = root.resolve()
    files = ["SKILL.md", *ADAPTER_REQUIREMENTS.keys()]
    results: dict[str, Any] = {"root": str(root), "files": {}, "ok": True}
    for rel in files:
        path = root / rel
        if not path.exists():
            results["files"][rel] = {"exists": False, "missing": ["file"]}
            results["ok"] = False
            continue
        text = path.read_text(encoding="utf-8")
        missing: dict[str, list[str]] = {}
        for name, terms in ROOT_REQUIREMENTS.items():
            absent = missing_terms(text, terms)
            if absent:
                missing[name] = absent
        if rel in ADAPTER_REQUIREMENTS:
            absent = missing_terms(text, ADAPTER_REQUIREMENTS[rel])
            if absent:
                missing["adapter_tools"] = absent
        results["files"][rel] = {"exists": True, "missing": missing}
        if missing:
            results["ok"] = False
    return results


def main() -> int:
    args = parse_args()
    report = check(args.root)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"Root: {report['root']}")
        print(f"OK: {report['ok']}")
        for rel, data in report["files"].items():
            print(f"- {rel}: {data}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
