#!/usr/bin/env python3
"""Deterministically ingest arXiv metadata into an llm-wiki sub-wiki."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import textwrap
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


ATOM_NS = {"a": "http://www.w3.org/2005/Atom"}
CONTENT_DIRS = ("entities", "concepts", "comparisons", "queries")


@dataclass(frozen=True)
class ArxivPaper:
    arxiv_id: str
    versioned_id: str
    title: str
    summary: str
    authors: tuple[str, ...]
    published: str
    updated: str
    categories: tuple[str, ...]
    abs_url: str
    pdf_url: str


def default_wiki_path() -> Path:
    raw = os.environ.get("LLM_WIKI_PATH") or os.environ.get("WIKI_PATH")
    if raw:
        return Path(raw).expanduser()
    return Path.home() / "wiki" / "llm-wiki"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest arXiv papers into llm-wiki")
    parser.add_argument("ids", nargs="*", help="arXiv IDs or https://arxiv.org/abs/... URLs")
    parser.add_argument("--wiki", type=Path, default=default_wiki_path())
    parser.add_argument("--metadata-file", type=Path, help="Offline arXiv Atom XML file")
    parser.add_argument("--dry-run", action="store_true", help="Plan changes without writing files")
    parser.add_argument("--force", action="store_true", help="Overwrite existing generated raw/page files")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    parser.add_argument("--today", help="Override YYYY-MM-DD for deterministic tests")
    parser.add_argument("--now", help="Override HH:MM for deterministic tests")
    return parser.parse_args()


def normalize_arxiv_id(raw: str) -> str:
    value = raw.strip()
    value = value.rstrip("/")
    if "/" in value:
        value = value.rsplit("/", 1)[-1]
    if value.endswith(".pdf"):
        value = value[:-4]
    match = re.match(r"(?P<id>(?:\d{4}\.\d{4,5}|[a-z.-]+/\d{7}))(?:v\d+)?$", value)
    if not match:
        raise ValueError(f"not an arXiv id or abs/pdf URL: {raw}")
    return match.group("id")


def slugify(text: str, max_length: int = 72) -> str:
    value = text.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    if len(value) > max_length:
        value = value[:max_length].rsplit("-", 1)[0] or value[:max_length]
    return value or "untitled"


def read_atom_xml(ids: list[str], metadata_file: Path | None) -> bytes:
    if metadata_file:
        return metadata_file.expanduser().read_bytes()
    if not ids:
        raise ValueError("provide at least one arXiv id or --metadata-file")
    query = urllib.parse.urlencode({"id_list": ",".join(ids), "max_results": str(len(ids))})
    url = f"https://export.arxiv.org/api/query?{query}"
    req = urllib.request.Request(url, headers={"User-Agent": "llm-wiki-codex-ingest/1.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read()


def text_of(entry: ET.Element, path: str) -> str:
    return " ".join((entry.findtext(path, default="", namespaces=ATOM_NS) or "").split())


def paper_from_entry(entry: ET.Element) -> ArxivPaper:
    entry_id = text_of(entry, "a:id").rsplit("/", 1)[-1]
    base_id = normalize_arxiv_id(entry_id)
    title = text_of(entry, "a:title")
    summary = text_of(entry, "a:summary")
    authors = tuple(
        " ".join((author.findtext("a:name", default="", namespaces=ATOM_NS) or "").split())
        for author in entry.findall("a:author", ATOM_NS)
    )
    categories = tuple(category.attrib.get("term", "") for category in entry.findall("a:category", ATOM_NS) if category.attrib.get("term"))
    published = text_of(entry, "a:published")[:10]
    updated = text_of(entry, "a:updated")[:10]
    return ArxivPaper(
        arxiv_id=base_id,
        versioned_id=entry_id,
        title=title,
        summary=summary,
        authors=authors,
        published=published,
        updated=updated,
        categories=categories,
        abs_url=f"https://arxiv.org/abs/{base_id}",
        pdf_url=f"https://arxiv.org/pdf/{base_id}",
    )


def parse_papers(atom_xml: bytes, requested_ids: list[str]) -> list[ArxivPaper]:
    root = ET.fromstring(atom_xml)
    papers = [paper_from_entry(entry) for entry in root.findall("a:entry", ATOM_NS)]
    if requested_ids:
        requested = {normalize_arxiv_id(item) for item in requested_ids}
        papers = [paper for paper in papers if paper.arxiv_id in requested]
    return sorted(papers, key=lambda paper: paper.arxiv_id)


def load_taxonomy(wiki: Path) -> set[str]:
    schema = wiki / "SCHEMA.md"
    if not schema.exists():
        return set()
    tags: set[str] = set()
    in_taxonomy = False
    for line in schema.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            in_taxonomy = "tag taxonomy" in stripped.lower()
            continue
        if in_taxonomy and stripped.startswith("- "):
            item = re.sub(r"^\*\*[^*]+\*\*:\s*", "", stripped[2:])
            for tag in item.split(","):
                clean = tag.strip().strip("`")
                if clean:
                    tags.add(clean)
    return tags


def existing_page_stems(wiki: Path) -> set[str]:
    stems: set[str] = {"index"}
    for directory in CONTENT_DIRS:
        root = wiki / directory
        if root.exists():
            stems.update(path.stem for path in root.rglob("*.md"))
    return stems


def source_already_ingested(wiki: Path, paper: ArxivPaper) -> str | None:
    needles = {paper.arxiv_id, paper.versioned_id, paper.abs_url}
    for directory in CONTENT_DIRS:
        root = wiki / directory
        if not root.exists():
            continue
        for path in root.rglob("*.md"):
            text = path.read_text(encoding="utf-8")
            if any(needle in text for needle in needles):
                return path.relative_to(wiki).as_posix()
    return None


def choose_tags(paper: ArxivPaper, taxonomy: set[str]) -> list[str]:
    haystack = f"{paper.title} {paper.summary}".lower()
    candidates = ["paper", "llm"]
    if "agent" in haystack or "tool" in haystack:
        candidates.extend(["agent", "tool-use"])
    if "retriev" in haystack or "rag" in haystack:
        candidates.extend(["RAG", "retrieval"])
    if "fine-tun" in haystack or "lora" in haystack:
        candidates.extend(["fine-tuning", "lora"])
    if "align" in haystack or "feedback" in haystack or "preference" in haystack:
        candidates.extend(["alignment", "RLHF"])
    if "context" in haystack:
        candidates.append("context-length")
    chosen: list[str] = []
    for tag in candidates:
        if tag in taxonomy and tag not in chosen:
            chosen.append(tag)
    return chosen or sorted(taxonomy)[:1] or ["paper"]


def choose_links(paper: ArxivPaper, wiki: Path, raw_rel: str) -> list[str]:
    stems = existing_page_stems(wiki)
    haystack = f"{paper.title} {paper.summary}".lower()
    candidates: list[str] = []
    rules = [
        ("lora", "lora"),
        ("qlora", "QLoRA"),
        ("quant", "quantization"),
        ("retriev", "rag-retrieval"),
        ("rag", "rag-retrieval"),
        ("agent", "agent-architectures"),
        ("tool", "agent-architectures"),
        ("reason", "chain-of-thought"),
        ("preference", "dpo"),
        ("align", "rlhf"),
        ("feedback", "rlhf"),
        ("context", "rag-retrieval"),
    ]
    for needle, link in rules:
        if needle in haystack and link in stems and link not in candidates:
            candidates.append(link)
    candidates.append(raw_rel.removesuffix(".md"))
    candidates.append("index")
    unique: list[str] = []
    for link in candidates:
        if link and link not in unique:
            unique.append(link)
    return unique[:4]


def raw_markdown(paper: ArxivPaper) -> str:
    authors = ", ".join(paper.authors)
    categories = ", ".join(paper.categories)
    return f"""---
kind: paper
arxiv_id: {paper.arxiv_id}
versioned_id: {paper.versioned_id}
source: {paper.abs_url}
pdf: {paper.pdf_url}
published: {paper.published}
updated: {paper.updated}
categories: [{categories}]
---

# {paper.title}

Authors: {authors}

Abstract:

{paper.summary}
"""


def concept_markdown(paper: ArxivPaper, today: str, tags: list[str], raw_rel: str, links: list[str]) -> str:
    link_lines = "\n".join(f"- [[{link}]]" for link in links)
    authors = ", ".join(paper.authors[:6])
    wrapped_summary = "\n".join(textwrap.wrap(paper.summary, width=100))
    return f"""---
title: {paper.title}
created: {today}
updated: {today}
type: summary
tags: [{", ".join(tags)}]
sources: [{raw_rel}]
---

# {paper.title}

## Bibliographic Record

- arXiv: [{paper.arxiv_id}]({paper.abs_url})
- PDF: {paper.pdf_url}
- Published: {paper.published}
- Updated: {paper.updated}
- Authors: {authors}

## Abstract Summary

{wrapped_summary}

## llm-wiki Test Notes

This page was generated by the deterministic Codex arXiv ingest helper. Use it as a starting point for a richer manual or agent-assisted synthesis pass.

## Related Links

{link_lines}
"""


def update_index_text(index_text: str, page_slug: str, title: str, today: str, total_pages: int) -> str:
    lines = index_text.splitlines()
    updated_lines: list[str] = []
    inserted = False
    concept_entry = f"- [[{page_slug}]] - {title}"
    for line in lines:
        if line.startswith("> Last updated:"):
            updated_lines.append(f"> Last updated: {today} | Total pages: {total_pages}")
            continue
        if not inserted and line.startswith("## Comparisons"):
            updated_lines.append(concept_entry)
            inserted = True
        updated_lines.append(line)
    if not inserted:
        updated_lines.extend(["", "## Concepts", concept_entry])
    return "\n".join(updated_lines).rstrip() + "\n"


def content_page_count(wiki: Path) -> int:
    total = 0
    for directory in CONTENT_DIRS:
        root = wiki / directory
        if root.exists():
            total += sum(1 for path in root.rglob("*.md") if path.is_file())
    return total


def append_log(wiki: Path, today: str, now: str, created: list[str], skipped: list[str]) -> None:
    log_dir = wiki / "log"
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / f"{today.replace('-', '')}.md"
    if path.exists():
        text = path.read_text(encoding="utf-8").rstrip() + "\n\n"
    else:
        text = f"# {today}\n\n"
    text += f"## [{now}] ingest | arXiv batch\n"
    if created:
        text += "- Created: " + ", ".join(created) + "\n"
    if skipped:
        text += "- Skipped: " + ", ".join(skipped) + "\n"
    path.write_text(text, encoding="utf-8")


def ingest(wiki: Path, papers: list[ArxivPaper], dry_run: bool, force: bool, today: str, now: str) -> dict[str, Any]:
    wiki = wiki.expanduser().resolve()
    if not (wiki / "SCHEMA.md").exists() or not (wiki / "index.md").exists():
        raise FileNotFoundError(f"{wiki} is not an llm-wiki root")

    taxonomy = load_taxonomy(wiki)
    plan: dict[str, Any] = {"wiki": str(wiki), "created": [], "updated": [], "skipped": []}
    created_pages: list[str] = []
    skipped: list[str] = []

    for paper in papers:
        existing = source_already_ingested(wiki, paper)
        if existing and not force:
            plan["skipped"].append({"arxiv_id": paper.arxiv_id, "reason": f"already referenced by {existing}"})
            skipped.append(paper.arxiv_id)
            continue

        raw_slug = f"{paper.arxiv_id}-{slugify(paper.title, 48)}"
        raw_rel = f"raw/papers/{raw_slug}.md"
        page_slug = slugify(paper.title)
        page_rel = f"concepts/{page_slug}.md"
        tags = choose_tags(paper, taxonomy)
        links = choose_links(paper, wiki, raw_rel)
        writes = [
            {"path": raw_rel, "kind": "raw"},
            {"path": page_rel, "kind": "page"},
        ]
        plan["created"].append({"arxiv_id": paper.arxiv_id, "title": paper.title, "writes": writes})

        if dry_run:
            continue

        raw_path = wiki / raw_rel
        page_path = wiki / page_rel
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        page_path.parent.mkdir(parents=True, exist_ok=True)
        if force or not raw_path.exists():
            raw_path.write_text(raw_markdown(paper), encoding="utf-8")
        if force or not page_path.exists():
            page_path.write_text(concept_markdown(paper, today, tags, raw_rel, links), encoding="utf-8")
        created_pages.append(page_rel)

        index_path = wiki / "index.md"
        total = content_page_count(wiki)
        index_path.write_text(update_index_text(index_path.read_text(encoding="utf-8"), page_slug, paper.title, today, total), encoding="utf-8")

    if not dry_run:
        append_log(wiki, today, now, created_pages, skipped)
    return plan


def main() -> int:
    args = parse_args()
    requested_ids = [normalize_arxiv_id(item) for item in args.ids]
    today = args.today or datetime.now().strftime("%Y-%m-%d")
    now = args.now or datetime.now().strftime("%H:%M")
    try:
        papers = parse_papers(read_atom_xml(requested_ids, args.metadata_file), requested_ids)
        if not papers:
            raise ValueError("no arXiv entries found")
        plan = ingest(args.wiki, papers, args.dry_run, args.force, today, now)
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(plan, indent=2, sort_keys=True))
    else:
        print(f"Wiki: {plan['wiki']}")
        for item in plan["created"]:
            print(f"create {item['arxiv_id']}: {item['title']}")
            for write in item["writes"]:
                print(f"  - {write['path']}")
        for item in plan["skipped"]:
            print(f"skip {item['arxiv_id']}: {item['reason']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
