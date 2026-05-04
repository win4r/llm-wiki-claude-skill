# Graph Report - llm-wiki-claude-skill  (2026-05-03)

## Corpus Check
- 2 files · ~10,639 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 30 nodes · 56 edges · 6 communities detected
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 1 edges (avg confidence: 0.8)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]

## God Nodes (most connected - your core abstractions)
1. `lint()` - 13 edges
2. `main()` - 8 edges
3. `LinkResolver` - 4 edges
4. `main()` - 4 edges
5. `parse_args()` - 3 edges
6. `parse_args()` - 3 edges
7. `parse_frontmatter_fallback()` - 3 edges
8. `parse_frontmatter()` - 3 edges
9. `rel_key()` - 3 edges
10. `collect_markdown()` - 3 edges

## Surprising Connections (you probably didn't know these)
- `lint()` --calls--> `parse_frontmatter()`  [EXTRACTED]
  llm_wiki_lint.py → llm_wiki_lint.py  _Bridges community 4 → community 1_
- `lint()` --calls--> `rel_key()`  [EXTRACTED]
  llm_wiki_lint.py → llm_wiki_lint.py  _Bridges community 3 → community 1_
- `lint()` --calls--> `collect_markdown()`  [EXTRACTED]
  llm_wiki_lint.py → llm_wiki_lint.py  _Bridges community 5 → community 1_
- `main()` --calls--> `lint()`  [EXTRACTED]
  llm_wiki_lint.py → llm_wiki_lint.py  _Bridges community 1 → community 2_

## Communities

### Community 0 - "Community 0"
Cohesion: 0.42
Nodes (8): container_readme_template(), default_wiki_path(), index_template(), main(), parse_args(), schema_template(), should_write_container_readme(), write_if_missing()

### Community 1 - "Community 1"
Cohesion: 0.46
Nodes (7): append_issue(), as_list(), collect_content_pages(), lint(), load_taxonomy(), parse_date(), word_count_without_frontmatter()

### Community 2 - "Community 2"
Cohesion: 0.5
Nodes (4): default_wiki_path(), main(), parse_args(), print_report()

### Community 3 - "Community 3"
Cohesion: 0.5
Nodes (2): LinkResolver, rel_key()

### Community 4 - "Community 4"
Cohesion: 0.67
Nodes (3): parse_frontmatter(), parse_frontmatter_fallback(), parse_scalar()

### Community 5 - "Community 5"
Cohesion: 1.0
Nodes (2): collect_markdown(), is_archived()

## Knowledge Gaps
- **Thin community `Community 3`** (4 nodes): `LinkResolver`, `.__init__()`, `.resolve()`, `rel_key()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 5`** (2 nodes): `collect_markdown()`, `is_archived()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `main()` connect `Community 0` to `Community 3`?**
  _High betweenness centrality (0.432) - this node is a cross-community bridge._
- **Why does `lint()` connect `Community 1` to `Community 2`, `Community 3`, `Community 4`, `Community 5`?**
  _High betweenness centrality (0.372) - this node is a cross-community bridge._
- **Why does `LinkResolver` connect `Community 3` to `Community 1`?**
  _High betweenness centrality (0.088) - this node is a cross-community bridge._