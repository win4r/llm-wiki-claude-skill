---
name: llm-wiki
description: Maintain a persistent research knowledge base at ~/wiki/llm-wiki using Karpathy's LLM Wiki pattern — interlinked markdown files for AI/LLM research, fine-tuning papers, and domain notes. Use when the user asks to ingest a paper/article/URL into the wiki, query the wiki, lint the wiki, compile/restructure the wiki (split oversized pages, merge duplicates, rebuild index), scaffold a new wiki, or save research notes. Distinct from Codex session memory (which tracks temporary working context) — this wiki is for durable research knowledge that compounds across sessions and across tools. Triggers include "加到wiki", "ingest this", "ask the wiki", "lint wiki", "compile wiki", "restructure wiki", "清理wiki", "归档到知识库", "save to wiki", "search my notes", "检索知识库", "scaffold wiki".
---

# LLM Wiki (Codex)

A persistent, interlinked markdown knowledge base at `~/wiki/llm-wiki/`. Based on [Karpathy's LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

Unlike RAG (which rediscovers knowledge per query), the wiki compiles knowledge once and keeps it current. Cross-references exist. Contradictions are flagged. Synthesis reflects everything ingested.

## Boundary: Wiki vs Codex session memory

| Store | Scope | Contains |
|---|---|---|
| **Wiki** (this skill) | `$LLM_WIKI_PATH`, `$WIKI_PATH`, or `~/wiki/llm-wiki/` | Shared, cross-session research knowledge — papers, concepts, entities, comparisons |
| **Codex session memory** | current thread / transient working context | Temporary task state, scratch notes, open questions, one-off execution context |

**Never mix them.** The wiki is a persistent research knowledge base shared across Claude Code, Hermes Agent, Obsidian, and Codex. Do not store transient session state in it: scratch plans, shell breadcrumbs, temporary reminders, or one-off TODOs belong in the current Codex session, not the wiki.

## Wiki Path

Resolve the active wiki path once per task and reuse it in every command:

```bash
WIKI="${LLM_WIKI_PATH:-${WIKI_PATH:-$HOME/wiki/llm-wiki}}"
```

Default is `~/wiki/llm-wiki/`. Use `$LLM_WIKI_PATH` or `$WIKI_PATH` to target another sub-wiki without editing this skill.

## Orient Before Acting (every session)

Before any ingest / query / lint, read these three in order. If the wiki does not exist and the user asked to create or scaffold one, run the bundled scaffold script first.

1. `exec_command`: `WIKI="${LLM_WIKI_PATH:-${WIKI_PATH:-$HOME/wiki/llm-wiki}}"; sed -n '1,220p' "$WIKI/SCHEMA.md"` — domain, conventions, tag taxonomy
2. `exec_command`: `WIKI="${LLM_WIKI_PATH:-${WIKI_PATH:-$HOME/wiki/llm-wiki}}"; sed -n '1,220p' "$WIKI/index.md"` — what pages exist
3. `exec_command`: `WIKI="${LLM_WIKI_PATH:-${WIKI_PATH:-$HOME/wiki/llm-wiki}}"; ls -1 "$WIKI/log" | tail -n 3`, then read the last 2–3 daily logs with `sed -n '1,220p' "$WIKI/log/YYYYMMDD.md"` — recent activity

Skipping orientation causes duplicate pages, missed cross-references, tag sprawl, and repeated work.

For queries on large wikis (100+ pages), also run `exec_command` with `rg -n "<topic>" "$WIKI" -g '*.md'` before creating anything new.

## Structure

**Multi-wiki container**: `~/wiki/` is a container that may hold multiple sub-wikis (e.g. `~/wiki/llm-wiki/`, `~/wiki/hermes-learn/`, future `~/wiki/<name>-wiki/`). This skill operates on `$WIKI` (`~/wiki/llm-wiki/` by default). A single Obsidian vault at the container root (`~/wiki/.obsidian/`) covers all sub-wikis, so cross-wiki `[[wikilinks]]` still work.

When adding a new sub-wiki, prefer the bundled script:

```bash
python3 ~/.codex/skills/llm-wiki/scripts/llm_wiki_scaffold.py --wiki "$HOME/wiki/<name>-wiki" --domain "<domain>"
```

It creates the tree below, starter `SCHEMA.md`, `index.md`, today's log file, and a container `README.md` if missing.

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
WIKI="${LLM_WIKI_PATH:-${WIKI_PATH:-$HOME/wiki/llm-wiki}}"
grep -rh "^## \[" "$WIKI/log/" | tail -20       # recent activity
grep -rh "^## \[.*\] lint" "$WIKI/log/"         # all lint runs
grep -rl "dpo" "$WIKI/log/"                     # days that touched dpo
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
| URL (article) | `web.open` or `web.search_query`, then `apply_patch` | `$WIKI/raw/articles/<slug>.md` |
| PDF / arxiv | `web.open` or `exec_command` (`curl -L`), then `apply_patch` | `$WIKI/raw/papers/<slug>.md` |
| Pasted text | `apply_patch` (`*** Add File`) | appropriate `raw/` subdir |

Name files descriptively: `raw/papers/lora-hu-2021.md`, `raw/articles/karpathy-llm-wiki-2026.md`.

Codex does not have a direct `WebFetch` equivalent that both browses and writes files. Use `web.open` / `web.search_query` to inspect remote content, and use `exec_command` with `curl -L` when you need an exact local download before normalizing or saving with `apply_patch`.

**Step 2 — Discuss takeaways** with the user (skip in automated/cron contexts).

**Step 3 — Check what already exists**

- `exec_command`: `WIKI="${LLM_WIKI_PATH:-${WIKI_PATH:-$HOME/wiki/llm-wiki}}"; sed -n '1,220p' "$WIKI/index.md"`
- `exec_command` with `rg` for entities/concepts across the wiki:
  ```bash
  WIKI="${LLM_WIKI_PATH:-${WIKI_PATH:-$HOME/wiki/llm-wiki}}"
  rg -l "LoRA" "$WIKI" -g '*.md'
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

1. `exec_command`: `WIKI="${LLM_WIKI_PATH:-${WIKI_PATH:-$HOME/wiki/llm-wiki}}"; sed -n '1,220p' "$WIKI/index.md"`
2. For wikis with 100+ pages, also `exec_command`: `rg -n "<term>" "$WIKI" -g '*.md'`
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

Run the bundled lint script via `exec_command`:

```bash
WIKI="${LLM_WIKI_PATH:-${WIKI_PATH:-$HOME/wiki/llm-wiki}}"
python3 ~/.codex/skills/llm-wiki/scripts/llm_wiki_lint.py --wiki "$WIKI"
```

Use `--strict` when lint is a validation gate and should exit non-zero if any issue is found. The script checks:

- Required root files and directories
- Frontmatter shape and required fields, including `sources`
- Tag taxonomy from `SCHEMA.md`
- Broken, ambiguous, and case-mismatched wikilinks
- Pages with fewer than 2 outbound links
- Orphans, index completeness, oversized pages, and stale pages
- Source paths that point at missing files

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

1. Orient with `exec_command`: read `$WIKI/SCHEMA.md`, `$WIKI/index.md`, and every file in the target subtree.
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
| Search wiki content | `exec_command` | Prefer `rg -n "<term>" "$WIKI" -g '*.md'` |
| List all pages | `exec_command` | Prefer `rg --files "$WIKI"` or `find "$WIKI" -name '*.md'` |
| Fetch URL/PDF | `web.open` / `web.search_query` / `exec_command` | Use `curl -L` via `exec_command` when you need a local download |
| Write new page | `apply_patch` | Use `*** Add File` |
| Update existing page | `apply_patch` | Use `*** Update File`; always bump `updated` date |
| Scaffold a wiki | `exec_command` | `python3 ~/.codex/skills/llm-wiki/scripts/llm_wiki_scaffold.py --wiki "$WIKI"` |
| Run lint script | `exec_command` | `python3 ~/.codex/skills/llm-wiki/scripts/llm_wiki_lint.py --wiki "$WIKI"` |
| Ingest arXiv metadata | `exec_command` | `python3 ~/.codex/skills/llm-wiki/scripts/llm_wiki_ingest_arxiv.py --wiki "$WIKI" <arxiv-id>` |
| Repair schema drift | `exec_command` | `python3 ~/.codex/skills/llm-wiki/scripts/llm_wiki_repair.py --wiki "$WIKI" --apply` |
| Plan compile work | `exec_command` | `python3 ~/.codex/skills/llm-wiki/scripts/llm_wiki_compile_plan.py --wiki "$WIKI" --json` |

## Pitfalls

- **Never modify `raw/`** — sources are immutable, corrections live in wiki pages
- **Always operate on `$WIKI`, not the `~/wiki/` container root** — otherwise lint and edits can cross sub-wiki boundaries
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
