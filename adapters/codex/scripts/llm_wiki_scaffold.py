#!/usr/bin/env python3
"""Create a non-destructive starter llm-wiki sub-wiki."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path


DIRS = (
    "log",
    "raw/articles",
    "raw/papers",
    "raw/transcripts",
    "raw/notes",
    "raw/assets",
    "raw/refs",
    "entities",
    "concepts",
    "comparisons",
    "queries",
    "_archive",
)


def default_wiki_path() -> Path:
    raw = os.environ.get("LLM_WIKI_PATH") or os.environ.get("WIKI_PATH")
    if raw:
        return Path(raw).expanduser()
    return Path.home() / "wiki" / "llm-wiki"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scaffold an llm-wiki sub-wiki")
    parser.add_argument(
        "--wiki",
        type=Path,
        default=default_wiki_path(),
        help="Wiki root. Defaults to $LLM_WIKI_PATH, $WIKI_PATH, or ~/wiki/llm-wiki.",
    )
    parser.add_argument(
        "--domain",
        default="AI/LLM research",
        help="Short domain label for SCHEMA.md.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite SCHEMA.md and index.md if they already exist.",
    )
    parser.add_argument(
        "--container-readme",
        choices=("auto", "always", "never"),
        default="auto",
        help="When to create a README.md in the parent wiki container.",
    )
    return parser.parse_args()


def write_if_missing(path: Path, text: str, force: bool) -> str:
    if path.exists() and not force:
        return f"kept {path}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return f"wrote {path}"


def schema_template(domain: str, today: str) -> str:
    return f"""# Wiki Schema

## Domain

**{domain}** — Use this sub-wiki for durable research knowledge that should compound across sessions.

## Conventions

- File names: lowercase, hyphenated, no spaces.
- Every wiki page starts with YAML frontmatter.
- Every concept/entity/comparison/query page has at least 2 outbound `[[wikilinks]]`.
- Every page must be listed in `index.md`.
- Raw sources in `raw/` are immutable. Corrections go in compiled pages.
- Every operation is appended to `log/YYYYMMDD.md`.

## Frontmatter

```yaml
---
title: Page Title
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: entity | concept | comparison | query | summary
tags: [from taxonomy below]
sources: [raw/articles/source-name.md]
---
```

## Tag Taxonomy

Add new tags here before using them.

**Core:**
- research, note, source, summary, synthesis, question

**AI Systems:**
- llm, model, agent, memory, retrieval, rag, tool-use, evaluation

**Engineering:**
- architecture, workflow, automation, dataset, benchmark, production

**Meta:**
- comparison, taxonomy, method, framework, open-question

## Page Thresholds

- Create a page when a concept/entity is central to one source or appears in 2+ sources.
- Update an existing page when new material refines it.
- Do not create pages for passing mentions.
- Split pages over ~1200 words into `concepts/<topic>/index.md` plus focused sub-pages.

## Created

Scaffolded {today}.
"""


def index_template(today: str) -> str:
    return f"""# Wiki Index

> Content catalog. Every wiki page listed under its type with a one-line summary.
> Last updated: {today} | Total pages: 0

## Entities
<!-- Alphabetical within section -->

## Concepts
<!-- Alphabetical within section -->

## Comparisons
<!-- Alphabetical within section -->

## Queries
<!-- Alphabetical within section -->
"""


def container_readme_template(subwiki_name: str) -> str:
    return f"""# Wiki Container

This directory is an Obsidian vault root containing one or more sub-wikis.

## Sub-wikis

- `{subwiki_name}/` — llm-wiki knowledge base
"""


def should_write_container_readme(container: Path, mode: str) -> bool:
    if mode == "always":
        return True
    if mode == "never":
        return False
    return container.name == "wiki" or (container / ".obsidian").exists() or (container / "README.md").exists()


def main() -> int:
    args = parse_args()
    wiki = args.wiki.expanduser().resolve()
    today = datetime.now().strftime("%Y-%m-%d")
    today_compact = datetime.now().strftime("%Y%m%d")

    messages: list[str] = []
    wiki.mkdir(parents=True, exist_ok=True)
    for directory in DIRS:
        path = wiki / directory
        path.mkdir(parents=True, exist_ok=True)
        messages.append(f"ensured {path}")

    messages.append(write_if_missing(wiki / "SCHEMA.md", schema_template(args.domain, today), args.force))
    messages.append(write_if_missing(wiki / "index.md", index_template(today), args.force))
    messages.append(
        write_if_missing(
            wiki / "log" / f"{today_compact}.md",
            f"# {today}\n\n## [00:00] create | scaffold wiki\n- Path: {wiki}\n",
            False,
        )
    )

    container = wiki.parent
    if should_write_container_readme(container, args.container_readme):
        messages.append(
            write_if_missing(
                container / "README.md",
                container_readme_template(wiki.name),
                False,
            )
        )
    else:
        messages.append(f"skipped container README outside wiki-like parent: {container}")

    print(f"Wiki scaffold: {wiki}")
    for message in messages:
        print(f"- {message}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
