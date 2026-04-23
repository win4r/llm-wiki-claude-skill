---
name: llm-wiki
description: Maintain a persistent research knowledge base at ~/wiki/llm-wiki using Karpathy's LLM Wiki pattern — interlinked markdown files for AI/LLM research, fine-tuning papers, and domain notes. Use when the user asks to ingest a paper/article/URL into the wiki, query the wiki, lint the wiki, compile/restructure the wiki (split oversized pages, merge duplicates, rebuild index), or save research notes. Distinct from Codex session memory (which tracks temporary working context) — this wiki is for durable research knowledge that compounds across sessions and across tools. Triggers include "加到wiki", "ingest this", "ask the wiki", "lint wiki", "compile wiki", "restructure wiki", "清理wiki", "归档到知识库", "save to wiki", "search my notes", "检索知识库".
---

# LLM Wiki (Codex)

A persistent, interlinked markdown knowledge base at `~/wiki/llm-wiki/`. Based on [Karpathy's LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

Unlike RAG (which rediscovers knowledge per query), the wiki compiles knowledge once and keeps it current. Cross-references exist. Contradictions are flagged. Synthesis reflects everything ingested.

## Boundary: Wiki vs Codex session memory

| Store | Scope | Contains |
|---|---|---|
| **Wiki** (this skill) | `~/wiki/llm-wiki/` | Shared, cross-session research knowledge — papers, concepts, entities, comparisons |
| **Codex session memory** | current thread / transient working context | Temporary task state, scratch notes, open questions, one-off execution context |

**Never mix them.** The wiki is a persistent research knowledge base shared across Claude Code, Hermes Agent, Obsidian, and Codex. Do not store transient session state in it: scratch plans, shell breadcrumbs, temporary reminders, or one-off TODOs belong in the current Codex session, not the wiki.

## Orient Before Acting (every session)

Before any ingest / query / lint, read these three in order:

1. `exec_command`: `sed -n '1,220p' ~/wiki/llm-wiki/SCHEMA.md` — domain, conventions, tag taxonomy
2. `exec_command`: `sed -n '1,220p' ~/wiki/llm-wiki/index.md` — what pages exist
3. `exec_command`: `ls -1 ~/wiki/llm-wiki/log/ | tail -n 3`, then read the last 2–3 daily logs with `sed -n '1,220p' ~/wiki/llm-wiki/log/YYYYMMDD.md` — recent activity

Skipping orientation causes duplicate pages, missed cross-references, tag sprawl, and repeated work.

For queries on large wikis (100+ pages), also run `exec_command` with `rg -n "<topic>" ~/wiki/llm-wiki -g '*.md'` before creating anything new.

## Structure

**Multi-wiki container**: `~/wiki/` is a container that may hold multiple sub-wikis (e.g. `~/wiki/llm-wiki/`, `~/wiki/hermes-learn/`, future `~/wiki/<name>-wiki/`). This skill operates on the `llm-wiki` sub-wiki by default. A single Obsidian vault at the container root (`~/wiki/.obsidian/`) covers all sub-wikis, so cross-wiki `[[wikilinks]]` still work.

When adding a new sub-wiki: `mkdir ~/wiki/<name>-wiki`, scaffold the same tree below, write a domain-specific `SCHEMA.md`, and update `~/wiki/README.md` to list it.

```
~/wiki/                      ← Container (Obsidian vault root)
├── .obsidian/               ← Shared vault config (covers all sub-wikis)
├── README.md                ← Container-level sub-wiki index
└── llm-wiki/                ← This skill operates here by default
    ├── SCHEMA.md            # Domain, conventions, tag taxonomy (read-first)
    ├── index.md             # Sectioned content catalog
    ├── log/                 # Per-day action log (YYYYMMDD.md)
    ├── raw/                 # Immutable sources — NEVER modify
    │   ├── articles/
    │   ├── papers/
    │   ├── transcripts/
    │   ├── assets/
    │   └── refs/            # Pointer files for large binaries kept outside raw/
    ├── entities/            # People, orgs, products, models
    ├── concepts/            # Topics, techniques, methods
    ├── comparisons/         # Side-by-side analyses
    ├── queries/             # Filed query answers worth keeping
    └── _archive/            # Superseded content (kept, de-indexed)
```

Raw sources in `raw/` are **immutable**. Corrections go in wiki pages, never in raw files.

**Log convention**: one markdown file per day at `log/YYYYMMDD.md`. H1 is the ISO date (`# 2026-04-23`), each entry is `## [HH:MM] <op> | <subject>` with a short bullet body. Ops: `ingest`, `query`, `lint`, `compile`, `create`, `update`, `merge`, `archive`, `migrate`. Grep across history:

```bash
grep -rh "^## \[" ~/wiki/llm-wiki/log/ | tail -20       # recent activity
grep -rh "^## \[.*\] lint"  ~/wiki/llm-wiki/log/        # all lint runs
grep -rl "dpo"              ~/wiki/llm-wiki/log/        # days that touched dpo
```

## Page Sizing & Divide-and-Conquer

Target page length: **400–1200 words**. One page = one scannable unit.

When a topic grows past ~1200 words, split into a subfolder:

```
concepts/<topic>/
├── index.md          # Overview + list of sub-pages with one-line summaries
├── <aspect-1>.md
├── <aspect-2>.md
└── <aspect-3>.md
```

In the wiki root `index.md`, show the hierarchy via indented bullets:

```
- [[concepts/<topic>/index|<topic>]] — one-line summary
    - [[concepts/<topic>/<aspect-1>]] — ...
    - [[concepts/<topic>/<aspect-2>]] — ...
```

One fat file covering seven aspects is unreadable, unlinkable, and produces noisy diffs. Seven focused files + an index page give navigation, selective reading, clean backlinks, and small audit targets.

**When to split**: during a `compile` pass (see Core Operations), not mid-ingest — splitting while ingesting fragments attention.

## Large Binaries: `raw/refs/` Pointer Files

Small text sources (md, txt, PDFs under ~10 MB, small images) → copy into `raw/<subfolder>/`.

Large binaries (videos, model weights, datasets, PDFs >10 MB) → **do not copy** into the wiki. Create a pointer at `raw/refs/<slug>.md`:

```markdown
---
kind: ref
external_path: /Volumes/external/models/llama-3-70b/
size: ~140 GB
---

Llama 3 70B weights, downloaded 2026-01-15 from HuggingFace. Used by [[lora]] experiments.
```

Wiki pages cite `[[raw/refs/<slug>]]` just like any other source. The wiki directory stays git-friendly and rsync-able without dragging binaries around.

## Diagrams & Math

- **Any flow, sequence, hierarchy, or state diagram** → mermaid. Never ASCII art — it rots fast and is unsearchable.

  ````markdown
  ```mermaid
  flowchart LR
      A[raw/paper.md] --> B[summary]
      B --> C[concept page]
      C --> D[index.md]
  ```
  ````

- **Any formula** → KaTeX. Inline `$f(x) = \sum_i w_i x_i$` or block:

  ```
  $$
  L_{DPO} = -\mathbb{E}[\log \sigma(\beta \log \frac{\pi(y_w|x)}{\pi_{ref}(y_w|x)} - \beta \log \frac{\pi(y_l|x)}{\pi_{ref}(y_l|x)})]
  $$
  ```

Both render in Obsidian (default settings) and in most Markdown viewers. ASCII diagrams and formulas are refactor-hostile, unsearchable, and don't survive copy-paste cleanly.

## Core Operations

### 1. Ingest — add a source to the wiki

**Step 1 — Capture raw source**

| Source | Tool | Destination |
|---|---|---|
| URL (article) | `web.open` or `web.search_query`, then `apply_patch` | `~/wiki/llm-wiki/raw/articles/<slug>.md` |
| PDF / arxiv | `web.open` or `exec_command` (`curl -L`), then `apply_patch` | `~/wiki/llm-wiki/raw/papers/<slug>.md` |
| Pasted text | `apply_patch` (`*** Add File`) | appropriate `raw/` subdir |

Name files descriptively: `raw/papers/lora-hu-2021.md`, `raw/articles/karpathy-llm-wiki-2026.md`.

Codex does not have a direct `WebFetch` equivalent that both browses and writes files. Use `web.open` / `web.search_query` to inspect remote content, and use `exec_command` with `curl -L` when you need an exact local download before normalizing or saving with `apply_patch`.

**Step 2 — Discuss takeaways** with the user (skip in automated/cron contexts).

**Step 3 — Check what already exists**

- `exec_command`: `sed -n '1,220p' ~/wiki/llm-wiki/index.md`
- `exec_command` with `rg` for entities/concepts across the wiki:
  ```bash
  rg -l "LoRA" ~/wiki/llm-wiki -g '*.md'
  ```
- This is the difference between a growing wiki and a pile of duplicates.

**Step 4 — Write or update pages** per SCHEMA.md thresholds

- **Create a page** when an entity/concept appears in 2+ sources OR is central to one source
- **Update an existing page** when the source adds or refines information — bump `updated` date
- **Don't create** pages for passing mentions, minor details, or things outside the domain
- Every new/updated page: **≥2 outbound `[[wikilinks]]`** to other pages
- Every tag must be in `SCHEMA.md`'s taxonomy — add new tags there *first*, then use them
- **Contradictions**: don't silently overwrite. Note both positions with dates + sources, set `contradictions: [page-name]` in frontmatter, flag for user

Required frontmatter on every page:
```yaml
---
title: Page Title
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: entity | concept | comparison | query | summary
tags: [from SCHEMA taxonomy]
sources: [raw/papers/source-name.md]
---
```

**Step 5 — Update navigation**

- Add new pages to `index.md` under the correct section, alphabetically within section
- Update "Total pages" count and "Last updated" in index header
- Append to `log/<today-YYYYMMDD>.md` (create the file with `# YYYY-MM-DD` H1 if today's doesn't exist yet):
  ```
  ## [HH:MM] ingest | <Source Title>
  - Raw: raw/papers/<slug>.md
  - Created: entities/X.md, concepts/Y.md
  - Updated: concepts/Z.md (added section on ...)
  ```

**Step 6 — Report** every file created/updated back to the user.

A single source commonly touches 5–15 wiki pages. That's the compounding effect.

### 2. Query — answer a question from the wiki

1. `exec_command`: `sed -n '1,220p' ~/wiki/llm-wiki/index.md`
2. For wikis with 100+ pages, also `exec_command`: `rg -n "<term>" ~/wiki/llm-wiki -g '*.md'`
3. `exec_command` to read the relevant pages with `sed -n` or `cat`
4. Synthesize. Cite the sources: "Based on [[lora]] and [[peft]]…"
5. **File the answer back** if it's a substantial synthesis / comparison / deep dive:
   - Create a page in `queries/` or `comparisons/` with required frontmatter
   - Add to index.md
   - Don't file trivial lookups — only answers that would be painful to re-derive
6. Append to `log/<today-YYYYMMDD>.md`:
   ```
   ## [HH:MM] query | <question>
   - Filed to: queries/<slug>.md  (or "not filed — trivial")
   ```

### 3. Lint — audit wiki health

Run a Python script via `exec_command` for programmatic checks. Inline template:

```bash
python3 <<'EOF'
import os, re, yaml
from pathlib import Path
from collections import defaultdict

WIKI = Path.home() / "wiki"
DIRS = ["entities", "concepts", "comparisons", "queries"]

# Collect all wiki pages
pages = {}
for d in DIRS:
    for p in (WIKI / d).glob("*.md"):
        pages[p.stem] = p

# Extract wikilinks and frontmatter
inbound = defaultdict(set)
issues = {"orphans": [], "broken_links": [], "missing_frontmatter": [], "unknown_tags": []}

# Load taxonomy from SCHEMA.md
schema = (WIKI / "SCHEMA.md").read_text()
taxonomy = set(re.findall(r"^- ([a-zA-Z0-9\-_, ]+)", schema, re.M))
taxonomy = {t.strip() for chunk in taxonomy for t in chunk.split(",")}

for name, path in pages.items():
    text = path.read_text()
    # Parse frontmatter
    fm_match = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not fm_match:
        issues["missing_frontmatter"].append(str(path))
        continue
    try:
        fm = yaml.safe_load(fm_match.group(1))
    except Exception:
        issues["missing_frontmatter"].append(str(path))
        continue
    # Check required fields
    required = {"title", "created", "updated", "type", "tags"}
    if not required.issubset(fm or {}):
        issues["missing_frontmatter"].append(f"{path} (missing: {required - set(fm or {})})")
    # Check tags against taxonomy
    for tag in (fm or {}).get("tags") or []:
        if tag not in taxonomy:
            issues["unknown_tags"].append(f"{path}: {tag}")
    # Wikilinks
    for link in re.findall(r"\[\[([^\]]+)\]\]", text):
        target = link.split("|")[0].split("#")[0].strip()
        if target in pages:
            inbound[target].add(name)
        else:
            issues["broken_links"].append(f"{path} -> [[{target}]]")

# Orphans: zero inbound links
for name in pages:
    if not inbound[name]:
        issues["orphans"].append(str(pages[name]))

# Index completeness
index_text = (WIKI / "index.md").read_text()
for name, path in pages.items():
    if name not in index_text:
        issues.setdefault("not_indexed", []).append(str(path))

# Report
for k, v in issues.items():
    print(f"\n## {k} ({len(v)})")
    for item in v[:20]:
        print(f"  - {item}")
    if len(v) > 20:
        print(f"  ... and {len(v)-20} more")
EOF
```

Other checks (add or run separately):
- **Stale pages**: `updated` date >90 days ago
- **Page size**: >1200 words → candidate for splitting via `compile` (see Page Sizing & Divide-and-Conquer)
- **Log rotation**: not needed — daily `log/YYYYMMDD.md` files stay naturally small and git-diff-friendly

Report findings grouped by severity: broken links > missing frontmatter > orphans > unknown tags > stale. Append to `log/<today-YYYYMMDD>.md`:
```
## [HH:MM] lint | N issues found
- broken_links: X, orphans: Y, unknown_tags: Z
```

### 4. Compile — restructure existing wiki content

Periodic structural maintenance: split oversized pages, merge near-duplicates, rebuild `index.md`. `lint` finds problems; `compile` fixes structural ones.

**When to run**
- After a batch ingest (5+ sources in a row)
- When an existing page has outgrown ~1200 words
- When `index.md` drifts from filesystem reality
- When the user says "clean up the wiki" / "restructure" / "refactor the wiki"

**Steps**

1. Orient with `exec_command`: read `~/wiki/llm-wiki/SCHEMA.md`, `~/wiki/llm-wiki/index.md`, and every file in the target subtree.
2. For each page over ~1200 words: plan a split into `concepts/<topic>/index.md + <aspect>.md` per the divide-and-conquer pattern. **Confirm the plan with the user before writing** — splits are structural and expensive to reverse.
3. For each pair of near-duplicate pages: propose a merge. Confirm, then rewrite as one.
4. Rewrite `index.md` so every page appears exactly once under the right section, with hierarchy via indented bullets for split topics.
5. Re-run `lint` as the final check — broken wikilinks are common after moves.
6. Log to `log/<today-YYYYMMDD>.md`:
  ```
  ## [HH:MM] compile | <what changed>
  - Split: concepts/lora.md (1800 words) → concepts/lora/{index,rank-r-choice,merging,limitations}.md
  - Merged: concepts/dpo.md + concepts/direct-preference.md → concepts/dpo.md
  - Rebuilt index.md (29 → 32 pages)
  ```

Compile is destructive — it moves files and rewrites pages. Always orient first, always confirm before applying, always re-lint after.

## Tool Mapping Reference

Codex tools used by this skill:

| Operation | Tool | Notes |
|---|---|---|
| Read a wiki page or SCHEMA | `exec_command` | Prefer `sed -n 'start,endp'` or `cat` for local files |
| Search wiki content | `exec_command` | Prefer `rg -n "<term>" ~/wiki/llm-wiki -g '*.md'` |
| List all pages | `exec_command` | Prefer `rg --files ~/wiki/llm-wiki` or `find ~/wiki/llm-wiki -name '*.md'` |
| Fetch URL/PDF | `web.open` / `web.search_query` / `exec_command` | Use `curl -L` via `exec_command` when you need a local download |
| Write new page | `apply_patch` | Use `*** Add File` |
| Update existing page | `apply_patch` | Use `*** Update File`; always bump `updated` date |
| Run lint script | `exec_command` | Python script above |

## Pitfalls

- **Never modify `raw/`** — sources are immutable, corrections live in wiki pages
- **Always orient first** — SCHEMA + index + recent log, every new session. Skipping causes duplicates.
- **Always update index.md and today's `log/YYYYMMDD.md`** — these are the navigational backbone; skipping makes the wiki decay
- **Don't create pages for passing mentions** — follow SCHEMA thresholds (2+ sources OR central to one)
- **Every page needs ≥2 outbound `[[wikilinks]]`** — isolated pages are invisible
- **Tags only from SCHEMA taxonomy** — freeform tags decay into noise; add new tags there first
- **Handle contradictions explicitly** — note both, mark in frontmatter, flag for user
- **Ask before mass updates** — if an ingest would touch 10+ existing pages, confirm scope first
- **Keep pages scannable** — target 400–1200 words per page; split oversized via `compile` into `concepts/<topic>/` subfolders
- **Don't cross-contaminate with Codex session memory** — research goes in wiki, transient task state stays in the current session

## Obsidian

The Obsidian vault is **`~/wiki/`** (the container), not any individual sub-wiki. `.obsidian/` lives at the container root so all sub-wikis share one graph view and one link namespace. Open `~/wiki/` in Obsidian for:
- `[[wikilinks]]` as clickable links
- Graph View for the knowledge network
- Dataview queries like `TABLE tags FROM "concepts" WHERE contains(tags, "lora")`

Set Obsidian's attachment folder to `raw/assets/` so `![[image.png]]` resolves.
