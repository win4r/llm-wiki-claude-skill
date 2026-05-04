#!/usr/bin/env python3
"""Lint a Karpathy-style llm-wiki directory.

The checker is intentionally dependency-light. If PyYAML is installed it will
use it for frontmatter; otherwise it falls back to a small parser that handles
the frontmatter shapes used by this skill.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any


CONTENT_DIRS = ("entities", "concepts", "comparisons", "queries")
REQUIRED_DIRS = CONTENT_DIRS + ("log", "raw")
REQUIRED_ROOT_FILES = ("SCHEMA.md", "index.md")
REQUIRED_FIELDS = {"title", "created", "updated", "type", "tags", "sources"}
VALID_TYPES = {"entity", "concept", "comparison", "query", "summary"}
MAX_WORDS = 1200
STALE_DAYS = 90

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?", re.S)
WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


ISSUE_ORDER = (
    "missing_required_root",
    "missing_required_dirs",
    "missing_frontmatter",
    "invalid_frontmatter",
    "missing_fields",
    "invalid_type",
    "invalid_dates",
    "unknown_tags",
    "missing_sources",
    "missing_source_files",
    "broken_links",
    "ambiguous_links",
    "case_mismatch_links",
    "low_outbound_links",
    "orphans",
    "not_indexed",
    "oversized_pages",
    "stale_pages",
)


def default_wiki_path() -> Path:
    raw = os.environ.get("LLM_WIKI_PATH") or os.environ.get("WIKI_PATH")
    if raw:
        return Path(raw).expanduser()
    return Path.home() / "wiki" / "llm-wiki"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Lint an llm-wiki sub-wiki")
    parser.add_argument(
        "--wiki",
        type=Path,
        default=default_wiki_path(),
        help="Wiki root. Defaults to $LLM_WIKI_PATH, $WIKI_PATH, or ~/wiki/llm-wiki.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 when any issue is found.",
    )
    parser.add_argument(
        "--max-items",
        type=int,
        default=50,
        help="Maximum items to print per issue category.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print a machine-readable JSON report instead of text.",
    )
    return parser.parse_args()


def parse_scalar(value: str) -> Any:
    value = value.strip()
    if not value:
        return ""
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [part.strip().strip("'\"") for part in inner.split(",") if part.strip()]
    if value.startswith(("'", '"')) and value.endswith(("'", '"')):
        return value[1:-1]
    return value


def parse_frontmatter_fallback(body: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    current_key: str | None = None
    for raw_line in body.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if current_key and stripped.startswith("- "):
            data.setdefault(current_key, [])
            if not isinstance(data[current_key], list):
                data[current_key] = [data[current_key]]
            data[current_key].append(parse_scalar(stripped[2:]))
            continue
        if not raw_line.startswith(" ") and ":" in line:
            key, value = line.split(":", 1)
            current_key = key.strip()
            data[current_key] = parse_scalar(value)
            continue
    return data


def parse_frontmatter(text: str) -> tuple[dict[str, Any] | None, str | None]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return None, "missing frontmatter block"
    body = match.group(1)
    try:
        import yaml  # type: ignore

        parsed = yaml.safe_load(body) or {}
        if not isinstance(parsed, dict):
            return None, "frontmatter is not a mapping"
        return parsed, None
    except Exception:
        try:
            return parse_frontmatter_fallback(body), None
        except Exception as exc:  # pragma: no cover - defensive fallback
            return None, str(exc)


def as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, tuple):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            return [
                item.strip().strip("'\"")
                for item in stripped[1:-1].split(",")
                if item.strip()
            ]
        if "," in stripped:
            return [item.strip() for item in stripped.split(",") if item.strip()]
        return [stripped] if stripped else []
    return [str(value).strip()]


def rel_key(wiki: Path, path: Path) -> str:
    return path.relative_to(wiki).with_suffix("").as_posix()


def is_archived(wiki: Path, path: Path) -> bool:
    try:
        return path.relative_to(wiki).parts[:1] == ("_archive",)
    except ValueError:
        return False


def collect_markdown(wiki: Path, include_archive: bool = False) -> list[Path]:
    return sorted(
        p
        for p in wiki.rglob("*.md")
        if p.is_file() and (include_archive or not is_archived(wiki, p))
    )


def collect_content_pages(wiki: Path) -> list[Path]:
    pages: list[Path] = []
    for directory in CONTENT_DIRS:
        root = wiki / directory
        if root.exists():
            pages.extend(sorted(p for p in root.rglob("*.md") if p.is_file()))
    return pages


def load_taxonomy(schema_path: Path) -> set[str]:
    if not schema_path.exists():
        return set()
    text = schema_path.read_text(encoding="utf-8")
    tags: set[str] = set()
    in_taxonomy = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            in_taxonomy = "tag taxonomy" in stripped.lower()
            continue
        if in_taxonomy and stripped.startswith("- "):
            item = stripped[2:]
            item = re.sub(r"^\*\*[^*]+\*\*:\s*", "", item)
            item = item.split("#", 1)[0]
            for tag in item.split(","):
                clean = tag.strip().strip("`")
                if clean:
                    tags.add(clean)
    return tags


class LinkResolver:
    def __init__(self, wiki: Path, files: list[Path]) -> None:
        self.exact: dict[str, set[str]] = defaultdict(set)
        self.lower: dict[str, set[str]] = defaultdict(set)
        for path in files:
            rel = rel_key(wiki, path)
            aliases = {rel, Path(rel).name}
            if rel.endswith("/index"):
                aliases.add(rel[: -len("/index")])
            for alias in aliases:
                self.exact[alias].add(rel)
                self.lower[alias.lower()].add(rel)

    def resolve(self, raw_target: str) -> tuple[str | None, str | None]:
        target = raw_target.split("|", 1)[0].split("#", 1)[0].strip()
        if not target or re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I):
            return "", None
        if target.endswith(".md"):
            target = target[:-3]
        target = target.lstrip("/")
        if target.startswith("./"):
            target = target[2:]
        candidates = [target]
        if not target.endswith("/index"):
            candidates.append(f"{target}/index")

        for candidate in candidates:
            matches = self.exact.get(candidate, set())
            if len(matches) == 1:
                return next(iter(matches)), None
            if len(matches) > 1:
                return None, "ambiguous"

        for candidate in candidates:
            matches = self.lower.get(candidate.lower(), set())
            if len(matches) == 1:
                return next(iter(matches)), "case_mismatch"
            if len(matches) > 1:
                return None, "ambiguous"

        return None, "broken"


def word_count_without_frontmatter(text: str) -> int:
    text = FRONTMATTER_RE.sub("", text, count=1)
    return len(re.findall(r"\b\w+\b", text))


def parse_date(value: Any) -> str | None:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str) and DATE_RE.match(value.strip()):
        return value.strip()
    return None


def append_issue(issues: dict[str, list[str]], category: str, message: str) -> None:
    issues.setdefault(category, []).append(message)


def lint(wiki: Path) -> tuple[dict[str, list[str]], int]:
    wiki = wiki.expanduser().resolve()
    issues: dict[str, list[str]] = {category: [] for category in ISSUE_ORDER}

    if not wiki.exists():
        append_issue(issues, "missing_required_root", f"{wiki} does not exist")
        return issues, 0
    if not wiki.is_dir():
        append_issue(issues, "missing_required_root", f"{wiki} is not a directory")
        return issues, 0

    for filename in REQUIRED_ROOT_FILES:
        if not (wiki / filename).exists():
            append_issue(issues, "missing_required_root", filename)
    for directory in REQUIRED_DIRS:
        if not (wiki / directory).is_dir():
            append_issue(issues, "missing_required_dirs", directory)

    all_markdown = collect_markdown(wiki)
    content_pages = collect_content_pages(wiki)
    resolver = LinkResolver(wiki, all_markdown)
    taxonomy = load_taxonomy(wiki / "SCHEMA.md")
    index_text = (wiki / "index.md").read_text(encoding="utf-8") if (wiki / "index.md").exists() else ""
    inbound: dict[str, set[str]] = defaultdict(set)
    today = datetime.now().date()
    stale_before = today - timedelta(days=STALE_DAYS)

    for path in content_pages:
        rel = rel_key(wiki, path)
        text = path.read_text(encoding="utf-8")
        fm, error = parse_frontmatter(text)
        if fm is None:
            category = "missing_frontmatter" if error and "missing" in error else "invalid_frontmatter"
            append_issue(issues, category, f"{rel}: {error}")
            continue

        missing = sorted(REQUIRED_FIELDS - set(fm))
        if missing:
            append_issue(issues, "missing_fields", f"{rel}: {', '.join(missing)}")

        page_type = str(fm.get("type", "")).strip()
        if page_type and page_type not in VALID_TYPES:
            append_issue(issues, "invalid_type", f"{rel}: {page_type}")

        for field in ("created", "updated"):
            if field in fm and parse_date(fm.get(field)) is None:
                append_issue(issues, "invalid_dates", f"{rel}: {field}={fm.get(field)!r}")

        updated = parse_date(fm.get("updated"))
        if updated:
            try:
                updated_date = datetime.strptime(updated, "%Y-%m-%d").date()
                if updated_date < stale_before:
                    append_issue(issues, "stale_pages", f"{rel}: updated {updated}")
            except ValueError:
                append_issue(issues, "invalid_dates", f"{rel}: updated={updated!r}")

        tags = as_list(fm.get("tags"))
        if not tags:
            append_issue(issues, "unknown_tags", f"{rel}: no tags")
        elif taxonomy:
            for tag in tags:
                if tag not in taxonomy:
                    append_issue(issues, "unknown_tags", f"{rel}: {tag}")

        sources = as_list(fm.get("sources"))
        if not sources:
            append_issue(issues, "missing_sources", rel)
        else:
            for source in sources:
                if re.match(r"^[a-z][a-z0-9+.-]*:", source, re.I):
                    continue
                source_path = wiki / source
                if not source_path.exists():
                    append_issue(issues, "missing_source_files", f"{rel}: {source}")

        links = WIKILINK_RE.findall(text)
        outbound_count = 0
        for raw_link in links:
            resolved, status = resolver.resolve(raw_link)
            if resolved == "":
                continue
            if status == "case_mismatch":
                append_issue(issues, "case_mismatch_links", f"{rel} -> [[{raw_link}]]")
            if resolved:
                outbound_count += 1
                inbound[resolved].add(rel)
            elif status == "broken":
                append_issue(issues, "broken_links", f"{rel} -> [[{raw_link}]]")
            elif status == "ambiguous":
                append_issue(issues, "ambiguous_links", f"{rel} -> [[{raw_link}]]")

        if outbound_count < 2:
            append_issue(issues, "low_outbound_links", f"{rel}: {outbound_count} outbound links")

        if word_count_without_frontmatter(text) > MAX_WORDS:
            append_issue(issues, "oversized_pages", f"{rel}: >{MAX_WORDS} words")

        rel_stem = Path(rel).name
        if f"[[{rel}" not in index_text and f"[[{rel_stem}" not in index_text:
            append_issue(issues, "not_indexed", rel)

    # The root index is the canonical navigation page. Count its wikilinks as
    # inbound links so newly ingested pages are not false-positive orphans.
    index_path = wiki / "index.md"
    if index_path.exists():
        for raw_link in WIKILINK_RE.findall(index_path.read_text(encoding="utf-8")):
            resolved, _ = resolver.resolve(raw_link)
            if resolved:
                inbound[resolved].add("index")

    for path in content_pages:
        rel = rel_key(wiki, path)
        if rel not in inbound:
            append_issue(issues, "orphans", rel)

    return issues, len(content_pages)


def print_report(wiki: Path, issues: dict[str, list[str]], page_count: int, max_items: int) -> int:
    total = sum(len(items) for items in issues.values())
    print(f"Wiki: {wiki.expanduser().resolve()}")
    print(f"Pages checked: {page_count}")
    print(f"Total issues: {total}")
    for category in ISSUE_ORDER:
        items = issues.get(category, [])
        print(f"\n## {category} ({len(items)})")
        for item in items[:max_items]:
            print(f"  - {item}")
        if len(items) > max_items:
            print(f"  ... and {len(items) - max_items} more")
    print("\nStatus: OK" if total == 0 else "\nStatus: ISSUES FOUND")
    return total


def build_report(wiki: Path, issues: dict[str, list[str]], page_count: int) -> dict[str, Any]:
    total = sum(len(items) for items in issues.values())
    return {
        "wiki": str(wiki.expanduser().resolve()),
        "pages_checked": page_count,
        "total_issues": total,
        "issues": issues,
        "status": "ok" if total == 0 else "issues_found",
    }


def main() -> int:
    args = parse_args()
    wiki = args.wiki.expanduser()
    issues, page_count = lint(wiki)
    if args.json:
        report = build_report(wiki, issues, page_count)
        print(json.dumps(report, indent=2, sort_keys=True))
        total = int(report["total_issues"])
    else:
        total = print_report(wiki, issues, page_count, args.max_items)
    if args.strict and total:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
