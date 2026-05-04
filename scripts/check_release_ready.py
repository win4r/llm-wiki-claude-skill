#!/usr/bin/env python3
"""Repository-level release readiness checks for llm-wiki skill adapters."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_PATHS = [
    "VERSION",
    ".github/workflows/ci.yml",
    "README.md",
    "SKILL.md",
    "adapters/codex/SKILL.md",
    "adapters/codex/agents/openai.yaml",
    "adapters/codex/scripts/llm_wiki_lint.py",
    "adapters/codex/scripts/llm_wiki_scaffold.py",
    "adapters/codex/scripts/llm_wiki_ingest_arxiv.py",
    "adapters/codex/scripts/llm_wiki_repair.py",
    "adapters/codex/scripts/llm_wiki_compile_plan.py",
    "adapters/codex/scripts/llm_wiki_adapter_parity.py",
    "tests/test_codex_adapter_regression.py",
    "tests/fixtures/arxiv/toolformer.atom",
]


def check() -> dict[str, Any]:
    missing = [path for path in REQUIRED_PATHS if not (ROOT / path).exists()]
    version_text = (ROOT / "VERSION").read_text(encoding="utf-8").strip() if (ROOT / "VERSION").exists() else ""
    version_ok = bool(re.match(r"^\d+\.\d+\.\d+$", version_text))
    readme = (ROOT / "README.md").read_text(encoding="utf-8") if (ROOT / "README.md").exists() else ""
    readme_terms = [
        "python3 -m unittest discover",
        "llm_wiki_scaffold.py",
        "llm_wiki_lint.py",
        "llm_wiki_ingest_arxiv.py",
        "VERSION",
    ]
    readme_missing = [term for term in readme_terms if term not in readme]
    return {
        "version": version_text,
        "version_ok": version_ok,
        "missing_paths": missing,
        "readme_missing_terms": readme_missing,
        "ok": not missing and version_ok and not readme_missing,
    }


def main() -> int:
    report = check()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
