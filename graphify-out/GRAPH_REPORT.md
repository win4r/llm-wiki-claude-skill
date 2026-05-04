# Graph Report - llm-wiki-claude-skill  (2026-05-03)

## Corpus Check
- 3 files · ~11,326 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 44 nodes · 73 edges · 8 communities detected
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 4 edges (avg confidence: 0.8)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]

## God Nodes (most connected - your core abstractions)
1. `lint()` - 16 edges
2. `main()` - 8 edges
3. `LintFixtureTests` - 4 edges
4. `ScaffoldRegressionTests` - 4 edges
5. `LinkResolver` - 4 edges
6. `main()` - 4 edges
7. `LintCliTests` - 3 edges
8. `parse_args()` - 3 edges
9. `parse_args()` - 3 edges
10. `parse_frontmatter_fallback()` - 3 edges

## Surprising Connections (you probably didn't know these)
- `lint()` --calls--> `parse_frontmatter()`  [EXTRACTED]
  adapters/codex/scripts/llm_wiki_lint.py → adapters/codex/scripts/llm_wiki_lint.py  _Bridges community 6 → community 2_
- `lint()` --calls--> `rel_key()`  [EXTRACTED]
  adapters/codex/scripts/llm_wiki_lint.py → adapters/codex/scripts/llm_wiki_lint.py  _Bridges community 5 → community 2_
- `lint()` --calls--> `collect_markdown()`  [EXTRACTED]
  adapters/codex/scripts/llm_wiki_lint.py → adapters/codex/scripts/llm_wiki_lint.py  _Bridges community 7 → community 2_
- `main()` --calls--> `lint()`  [EXTRACTED]
  adapters/codex/scripts/llm_wiki_lint.py → adapters/codex/scripts/llm_wiki_lint.py  _Bridges community 2 → community 3_

## Communities

### Community 0 - "Community 0"
Cohesion: 0.22
Nodes (4): LintCliTests, LintFixtureTests, load_lint_module(), setUpClass()

### Community 1 - "Community 1"
Cohesion: 0.42
Nodes (8): container_readme_template(), default_wiki_path(), index_template(), main(), parse_args(), schema_template(), should_write_container_readme(), write_if_missing()

### Community 2 - "Community 2"
Cohesion: 0.46
Nodes (7): append_issue(), as_list(), collect_content_pages(), lint(), load_taxonomy(), parse_date(), word_count_without_frontmatter()

### Community 3 - "Community 3"
Cohesion: 0.4
Nodes (4): default_wiki_path(), main(), parse_args(), print_report()

### Community 4 - "Community 4"
Cohesion: 0.5
Nodes (1): ScaffoldRegressionTests

### Community 5 - "Community 5"
Cohesion: 0.67
Nodes (2): LinkResolver, rel_key()

### Community 6 - "Community 6"
Cohesion: 0.67
Nodes (3): parse_frontmatter(), parse_frontmatter_fallback(), parse_scalar()

### Community 7 - "Community 7"
Cohesion: 1.0
Nodes (2): collect_markdown(), is_archived()

## Knowledge Gaps
- **Thin community `Community 4`** (4 nodes): `ScaffoldRegressionTests`, `.test_scaffold_container_readme_always_mode()`, `.test_scaffold_creates_lint_clean_empty_wiki()`, `.test_scaffold_preserves_existing_schema_without_force()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 5`** (3 nodes): `LinkResolver`, `.__init__()`, `rel_key()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 7`** (2 nodes): `collect_markdown()`, `is_archived()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `lint()` connect `Community 2` to `Community 0`, `Community 3`, `Community 5`, `Community 6`, `Community 7`?**
  _High betweenness centrality (0.618) - this node is a cross-community bridge._
- **Why does `main()` connect `Community 1` to `Community 3`?**
  _High betweenness centrality (0.318) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `lint()` (e.g. with `.test_valid_fixture_has_no_lint_issues()` and `.test_archived_duplicate_does_not_make_active_link_ambiguous()`) actually correct?**
  _`lint()` has 3 INFERRED edges - model-reasoned connections that need verification._