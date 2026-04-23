# llm-wiki — Claude Code Skill

> Build and maintain a persistent, interlinked markdown knowledge base as a Claude Code skill.
> Based on [Andrej Karpathy's LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

A single-file `SKILL.md` that teaches Claude Code how to treat a directory of markdown files (default `~/wiki/`) as a compounding, self-organizing research knowledge base. Four core operations — **ingest**, **query**, **lint**, **compile** — turn raw sources (papers, articles, URLs) into cross-linked concept pages, without requiring any external RAG service.

## Why a wiki instead of RAG?

- **RAG** re-retrieves raw chunks on every query. Knowledge never compiles.
- **LLM Wiki** compiles raw sources **once** into cross-linked markdown pages. Contradictions are flagged. Synthesis reflects everything ingested. Every ingest makes the wiki richer — not the retrieval index.

For deep-dive research (reading papers over weeks, building a personal encyclopedia, curating a team knowledge base), the wiki pattern compounds where RAG forgets.

## Features

- **Four core operations**: ingest sources, query the wiki, lint for health, compile (restructure) oversized content
- **Divide-and-conquer pages**: target 400–1200 words per page; auto-split into `concepts/<topic>/<aspect>.md` subfolders when a topic outgrows a single file
- **Taxonomy discipline**: every tag must come from `SCHEMA.md`; lint flags freeform tags
- **Cross-reference enforcement**: every page needs ≥2 outbound `[[wikilinks]]`; lint finds orphans and broken links
- **Pointer files for large binaries**: `raw/refs/<slug>.md` avoids bloating the repo with model weights, datasets, or large PDFs
- **Mermaid + KaTeX**: required for diagrams and formulas — ASCII art rots and is unsearchable
- **Per-day log files**: `log/YYYYMMDD.md` — grep-friendly, git-diff-friendly, naturally small
- **Obsidian-compatible out of the box**: point Obsidian at `~/wiki/` for graph view, backlinks, dataview queries
- **Bilingual triggers**: recognizes both English and 中文 phrases (`"ingest this"` / `"加到wiki"`, `"lint wiki"` / `"清理wiki"`, etc.)

## Install

```bash
git clone https://github.com/win4r/llm-wiki-claude-skill ~/llm-wiki-claude-skill
mkdir -p ~/.claude/skills/llm-wiki
cp ~/llm-wiki-claude-skill/SKILL.md ~/.claude/skills/llm-wiki/SKILL.md
```

Claude Code picks up the skill on next session. Verify with `/skills` — you should see `llm-wiki` in the list.

## Install for other agents

The `adapters/` folder contains pre-ported versions for two other agent CLIs. All three point at the same wiki under `~/wiki/` — an ingest from any agent is immediately visible to all.

**Hermes Agent:**

```bash
mkdir -p ~/.hermes/skills/research/llm-wiki
cp adapters/hermes/SKILL.md ~/.hermes/skills/research/llm-wiki/SKILL.md
echo "WIKI_PATH=$HOME/wiki/llm-wiki" >> ~/.hermes/.env   # or any sub-wiki path
```

Hermes adapter uses `read_file` / `write_file` / `apply_patch` / `search_files` / `web_extract` / `execute_code`. Its lint script honors `$WIKI_PATH`, so a single env-var change points Hermes at any sub-wiki without editing the skill.

**Codex CLI:**

```bash
mkdir -p ~/.codex/skills/llm-wiki
cp adapters/codex/SKILL.md ~/.codex/skills/llm-wiki/SKILL.md
```

Codex adapter uses `exec_command` / `apply_patch` / `web.open` / `rg`. Default sub-wiki is `~/wiki/llm-wiki/`; to target a different sub-wiki, sed-replace the path or keep a local fork.

### Tool-vocabulary mapping (for forks)

| Canonical (Claude Code) | Hermes | Codex |
|---|---|---|
| `Read` | `read_file` | `exec_command sed -n '1,220p' …` |
| `Write` | `write_file` | `apply_patch '*** Add File: …'` |
| `Edit` | `apply_patch` | `apply_patch '*** Update File: …'` |
| `Grep` | `search_files(pattern:)` | `exec_command rg -n …` |
| `Glob` | `search_files(target: "files")` | `exec_command rg --files / find -name` |
| `WebFetch` | `web_extract` | `web.open` + `apply_patch` (two-step) |
| `Bash` | `execute_code` | `exec_command` |

Canonical `SKILL.md` at the repo root is the source of truth; adapters are ported by sed-mapping the tool vocabulary above. When the canonical version changes, re-port the diff into each adapter.

## Usage

Talk to Claude Code in natural language. The skill triggers on phrases like:

| Operation | Example triggers |
|---|---|
| **Ingest** | `ingest this paper: https://arxiv.org/abs/2305.18290`, `把这篇加到wiki` |
| **Query** | `ask the wiki about DPO vs RLHF`, `检索知识库` |
| **Lint** | `lint wiki`, `wiki 体检`, `health check the wiki` |
| **Compile** | `compile wiki`, `restructure the wiki`, `清理wiki` |

### Initializing a new wiki

If `~/wiki/llm-wiki/` doesn't exist yet, ask Claude:

> scaffold a new llm-wiki sub-wiki at ~/wiki/llm-wiki/ for AI research

It will create the directory tree and a starter `SCHEMA.md` customized to your domain.

### Example ingest flow

```
You:   ingest https://arxiv.org/abs/2305.18290 (DPO paper)

Claude: [reads SCHEMA.md, index.md, recent log/ days]
        [WebFetches the paper → saves raw/papers/2305.18290-dpo.md]
        [Greps for existing DPO/RLHF pages → finds none]
        [Creates concepts/dpo.md + concepts/rlhf.md]
        [Updates concepts/instruction-tuning.md with new cross-links]
        [Updates index.md: +2 pages]
        [Appends to log/20260423.md: ## [14:32] ingest | DPO paper ...]
        [Reports: 3 files created, 2 updated]
```

One source commonly touches 5–15 wiki pages. That's the compounding effect.

## Wiki structure (multi-wiki container)

`~/wiki/` is a **container** that holds one or more sub-wikis. This skill operates on the `llm-wiki` sub-wiki by default. A single Obsidian vault at the container root covers all sub-wikis.

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

### Adding more sub-wikis later

```bash
mkdir ~/wiki/dev-wiki        # or journal-wiki, reading-wiki, etc.
# Scaffold the same tree; define its own SCHEMA.md with a different domain
```

One Obsidian vault, one backup target, isolated taxonomies.

## Lint script

The SKILL.md embeds a self-contained Python lint script that checks:

- Orphan pages (no inbound wikilinks)
- Broken wikilinks (pointing to missing pages)
- Missing frontmatter (required fields + YAML validity)
- Unknown tags (not in SCHEMA.md taxonomy)
- Index completeness (every page listed in index.md)
- Page size (>1200 words → candidate for split via `compile`)

Run with: ask Claude `lint wiki`. Zero external dependencies beyond Python 3 + PyYAML.

## Real-world example: seeding a new sub-wiki

Actual workflow used to create `~/wiki/hermes-learn/` from 13 existing Markdown notes on the desktop:

```text
~/Desktop/doc/*.md (13 Hermes practice notes, ~348 KB total)
        │
        ▼
Phase 1 — scaffold ~/wiki/hermes-learn/
  mkdir -p log raw/{articles,papers,notes,assets,refs} entities concepts comparisons queries _archive
  Write SCHEMA.md (domain: Hermes Agent Practice; 84-tag taxonomy)
  Write initial index.md + log/YYYYMMDD.md
        │
        ▼
Phase 2 — batch ingest
  cp ~/Desktop/doc/*.md ~/wiki/hermes-learn/raw/notes/
  cp ~/Desktop/doc/*.html ~/wiki/hermes-learn/raw/assets/
        │
        ▼
Phase 3 — compile (concepts ≠ 1-to-1 with notes)
  2 entities:  hermes-agent, hermes-v0.10.0
  6 concepts:  delegation (merged from 5 notes), subagent, execute-code,
               multi-agent-emergent, dual-brain-architecture, cost-optimization
  Result: 8 pages, 4-7 inbound wikilinks each — dense cross-reference network
        │
        ▼
Phase 4 — lint pass: 0 issues
```

Key insight: **13 raw notes compiled to 8 wiki pages** (≈0.6 ratio). Five separate delegation notes merged into a single `delegation` concept — the compounding value is in the compiled structure, not 1-to-1 archival. Raw originals stay immutable in `raw/notes/` for traceability.

This is the pattern for any new sub-wiki: scaffold → bulk-copy raw sources → compile concepts (not duplicate them) → lint.

## Credits

- [Andrej Karpathy's LLM Wiki Gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) — the original concept
- [lewislulu/llm-wiki-skill](https://github.com/lewislulu/llm-wiki-skill) — OpenClaw / Codex variant with Obsidian plugin + web viewer. This repo borrows the `compile` operation, page-sizing rules, `raw/refs/` pointer convention, and per-day `log/` format.

## License

MIT — see [LICENSE](LICENSE).

---

# llm-wiki — Claude Code 技能（中文）

> 将 Claude Code 变成能持续编译、自我组织的知识库工具。
> 基于 [Andrej Karpathy 的 LLM Wiki 模式](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)。

单文件 `SKILL.md`，告诉 Claude Code 如何把一个 markdown 目录（默认 `~/wiki/`）当作持续增长、自动交叉引用的研究知识库。四个核心操作 — **ingest（归档源）**、**query（查询）**、**lint（健康检查）**、**compile（结构重构）** — 把原始材料（论文、文章、URL）编译成彼此链接的概念页，不需要任何外部 RAG 服务。

## 为什么是 wiki 而不是 RAG？

- **RAG** 每次查询都重新检索原始片段。知识从未被「编译」。
- **LLM Wiki** 把原始材料**一次性**编译成交叉引用的 markdown 页。矛盾被显式标记，综合反映所有已归档的内容。每次 ingest 让 wiki 变得更丰富 —— 而不只是让检索索引变臃肿。

对长期研究（连读几周的论文、搭建个人百科、团队知识库），wiki 模式会复利，RAG 则只会遗忘。

## 特性

- **四个核心操作**：ingest（归档）/ query（查询）/ lint（健康检查）/ compile（重构超长页面）
- **页面分治**：每页目标 400–1200 词，超过自动拆分为 `concepts/<topic>/<aspect>.md` 子目录
- **Taxonomy 约束**：所有 tag 必须来自 `SCHEMA.md`；lint 会标记野 tag
- **交叉引用强制**：每页至少 2 个出链 `[[wikilinks]]`；lint 找孤儿页和坏链
- **大二进制指针文件**：`raw/refs/<slug>.md` 避免把 model weights / 数据集 / 大 PDF 塞进仓库
- **Mermaid + KaTeX**：图和公式必须用它们 —— ASCII 绘图会腐烂且无法搜索
- **按天日志**：`log/YYYYMMDD.md`，git-diff 友好，天然小文件
- **原生兼容 Obsidian**：把 Obsidian 指向 `~/wiki/` 即可用 graph view、反向链接、dataview
- **中英双语触发词**：同时识别英文和中文（`"ingest this"` / `"加到wiki"`, `"lint wiki"` / `"清理wiki"` 等）

## 安装

```bash
git clone https://github.com/win4r/llm-wiki-claude-skill ~/llm-wiki-claude-skill
mkdir -p ~/.claude/skills/llm-wiki
cp ~/llm-wiki-claude-skill/SKILL.md ~/.claude/skills/llm-wiki/SKILL.md
```

下次启动 Claude Code 会自动识别。`/skills` 命令列表里应该看得到 `llm-wiki`。

## 其他 agent 安装

`adapters/` 目录包含针对另外两个 agent CLI 预先适配好的版本。三方都指向 `~/wiki/` 下的同一 wiki — 任何 agent 的 ingest，其他 agent 立即可见。

**Hermes Agent:**

```bash
mkdir -p ~/.hermes/skills/research/llm-wiki
cp adapters/hermes/SKILL.md ~/.hermes/skills/research/llm-wiki/SKILL.md
echo "WIKI_PATH=$HOME/wiki/llm-wiki" >> ~/.hermes/.env   # 或任意 sub-wiki 路径
```

Hermes 适配版用 `read_file` / `write_file` / `apply_patch` / `search_files` / `web_extract` / `execute_code`。lint 脚本识别 `$WIKI_PATH`，只改环境变量就能让 Hermes 切到其他 sub-wiki，不用改 skill 文件。

**Codex CLI:**

```bash
mkdir -p ~/.codex/skills/llm-wiki
cp adapters/codex/SKILL.md ~/.codex/skills/llm-wiki/SKILL.md
```

Codex 适配版用 `exec_command` / `apply_patch` / `web.open` / `rg`。默认 sub-wiki 是 `~/wiki/llm-wiki/`；要切到别的 sub-wiki 就 sed 替换路径，或者维护本地 fork。

### 工具词汇映射表（fork 参考）

| Canonical (Claude Code) | Hermes | Codex |
|---|---|---|
| `Read` | `read_file` | `exec_command sed -n '1,220p' …` |
| `Write` | `write_file` | `apply_patch '*** Add File: …'` |
| `Edit` | `apply_patch` | `apply_patch '*** Update File: …'` |
| `Grep` | `search_files(pattern:)` | `exec_command rg -n …` |
| `Glob` | `search_files(target: "files")` | `exec_command rg --files / find -name` |
| `WebFetch` | `web_extract` | `web.open` + `apply_patch` (两步) |
| `Bash` | `execute_code` | `exec_command` |

Repo 根目录的 `SKILL.md` 是 source of truth；adapters 通过上表的 sed 映射 port 过来。canonical 版改动后，把 diff 重新 port 到每个 adapter。

## 使用

用自然语言跟 Claude Code 对话。触发词示例：

| 操作 | 示例触发词 |
|---|---|
| **Ingest** | `把这篇论文加到wiki: https://arxiv.org/abs/2305.18290`、`ingest this` |
| **Query** | `ask the wiki about DPO vs RLHF`、`检索知识库关于...` |
| **Lint** | `lint wiki`、`wiki 体检`、`health check the wiki` |
| **Compile** | `清理wiki`、`compile wiki`、`restructure wiki` |

### 初始化新 wiki

如果还没有 `~/wiki/llm-wiki/`，告诉 Claude：

> 在 ~/wiki/llm-wiki 搭建一个新的 AI 研究知识库

它会建目录树 + 为你的领域定制 `SCHEMA.md`。

### Ingest 流程示例

```
你：   把 https://arxiv.org/abs/2305.18290 (DPO 论文) 加到 wiki

Claude: [读 SCHEMA.md、index.md、最近几天的 log/]
        [WebFetch 论文 → 存到 raw/papers/2305.18290-dpo.md]
        [Grep 查找现有 DPO/RLHF 页 → 未找到]
        [创建 concepts/dpo.md + concepts/rlhf.md]
        [更新 concepts/instruction-tuning.md 加入新交叉引用]
        [更新 index.md：+2 页]
        [追加到 log/20260423.md：## [14:32] ingest | DPO paper ...]
        [汇报：新建 3 个文件，更新 2 个]
```

一个源通常会触发 5–15 个 wiki 页面的改动 —— 这就是复利效应。

## 目录结构（多 wiki 容器）

`~/wiki/` 是一个**容器**，包含一个或多个 sub-wiki。本 skill 默认操作 `llm-wiki` 子目录。单一 Obsidian vault 位于容器根，覆盖所有 sub-wiki。

```
~/wiki/                      ← 容器（Obsidian vault 根）
├── .obsidian/               ← 共享 vault 配置（覆盖所有 sub-wiki）
├── README.md                ← 容器级 sub-wiki 索引
└── llm-wiki/                ← 本 skill 默认操作这里
    ├── SCHEMA.md            # 领域、约定、tag taxonomy（每个 session 先读）
    ├── index.md             # 分节目录
    ├── log/                 # 按天操作日志（YYYYMMDD.md）
    ├── raw/                 # 不可变源材料 —— 永不修改
    │   ├── articles/
    │   ├── papers/
    │   ├── transcripts/
    │   ├── assets/
    │   └── refs/            # 大二进制指针文件（实际文件放在 wiki 之外）
    ├── entities/            # 人、组织、产品、模型
    ├── concepts/            # 主题、技术、方法
    ├── comparisons/         # 横向对比
    ├── queries/             # 有保留价值的查询结果
    └── _archive/            # 被替代的内容（保留但移出索引）
```

### 未来添加更多 sub-wiki

```bash
mkdir ~/wiki/dev-wiki        # 或 journal-wiki、reading-wiki 等
# 搭建同样的目录树；定义独立的 SCHEMA.md（不同领域）
```

一个 Obsidian vault、一个备份目标、独立的 taxonomy 互不污染。

## Lint 脚本

SKILL.md 内嵌了一个独立 Python lint 脚本，检查：

- 孤儿页（没有入链）
- 坏 wikilink（指向不存在的页）
- 缺 frontmatter（缺必填字段 + YAML 语法）
- 野 tag（不在 SCHEMA.md taxonomy 里）
- 索引完整性（每页都在 index.md 里）
- 页面大小（>1200 词 → 候选通过 `compile` 拆分）

使用：对 Claude 说 `lint wiki`。外部依赖仅 Python 3 + PyYAML。

## 实战示例：从现有笔记种一个新 sub-wiki

真实工作流，用来把桌面 13 篇笔记做成 `~/wiki/hermes-learn/`：

```text
~/Desktop/doc/*.md (13 篇 Hermes 实践笔记，共 ~348 KB)
        │
        ▼
阶段 1 — scaffold ~/wiki/hermes-learn/
  mkdir -p log raw/{articles,papers,notes,assets,refs} entities concepts comparisons queries _archive
  写 SCHEMA.md（domain: Hermes Agent Practice；84-tag taxonomy）
  写初始 index.md + log/YYYYMMDD.md
        │
        ▼
阶段 2 — 批量 ingest
  cp ~/Desktop/doc/*.md ~/wiki/hermes-learn/raw/notes/
  cp ~/Desktop/doc/*.html ~/wiki/hermes-learn/raw/assets/
        │
        ▼
阶段 3 — compile（概念不是 1 对 1 映射笔记）
  2 entities:  hermes-agent, hermes-v0.10.0
  6 concepts:  delegation（合并自 5 篇笔记）、subagent、execute-code、
               multi-agent-emergent、dual-brain-architecture、cost-optimization
  结果：8 个页面，每页 4-7 个入链，稠密交叉引用网络
        │
        ▼
阶段 4 — lint 通过：0 issues
```

关键洞察：**13 篇原笔记编译成 8 页 wiki**（约 0.6 比例）。5 篇独立的 delegation 笔记合并为 1 个 `delegation` concept — 复利价值在**编译后的结构**，不在 1 对 1 归档。原笔记不可变地保存在 `raw/notes/` 里，随时追溯。

这是任意新 sub-wiki 的模式：scaffold → 批量拷贝 raw → compile 概念（不是复制）→ lint。

## 致谢

- [Andrej Karpathy 的 LLM Wiki Gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) —— 原始概念
- [lewislulu/llm-wiki-skill](https://github.com/lewislulu/llm-wiki-skill) —— OpenClaw / Codex 变体（含 Obsidian 插件和 Web viewer）。本仓库借鉴了 `compile` 操作、页面大小规则、`raw/refs/` 指针文件模式、按天 `log/` 格式。

## 许可证

MIT —— 见 [LICENSE](LICENSE)。
