# Graph Report - llm-wiki-claude-skill  (2026-05-03)

## Corpus Check
- 8 files · ~14,651 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 103 nodes · 173 edges · 8 communities detected
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 9 edges (avg confidence: 0.8)
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
2. `ingest()` - 13 edges
3. `main()` - 8 edges
4. `build_plan()` - 6 edges
5. `repair()` - 6 edges
6. `main()` - 6 edges
7. `LintCliTests` - 5 edges
8. `main()` - 5 edges
9. `paper_from_entry()` - 5 edges
10. `LintFixtureTests` - 4 edges

## Surprising Connections (you probably didn't know these)
- None detected - all connections are within the same source files.

## Communities

### Community 0 - "Community 0"
Cohesion: 0.15
Nodes (20): append_issue(), as_list(), build_report(), collect_content_pages(), collect_markdown(), default_wiki_path(), is_archived(), LinkResolver (+12 more)

### Community 1 - "Community 1"
Cohesion: 0.19
Nodes (21): append_log(), ArxivPaper, choose_links(), choose_tags(), concept_markdown(), content_page_count(), default_wiki_path(), existing_page_stems() (+13 more)

### Community 2 - "Community 2"
Cohesion: 0.1
Nodes (8): ArxivIngestE2ETests, CompilePlanTests, LintCliTests, load_lint_module(), ParityAndReleaseTests, RepairRegressionTests, ScaffoldRegressionTests, setUpClass()

### Community 3 - "Community 3"
Cohesion: 0.42
Nodes (8): container_readme_template(), default_wiki_path(), index_template(), main(), parse_args(), schema_template(), should_write_container_readme(), write_if_missing()

### Community 4 - "Community 4"
Cohesion: 0.42
Nodes (8): content_pages(), default_wiki_path(), has_nonempty_sources(), main(), parse_args(), placeholder_text(), repair(), repair_frontmatter()

### Community 5 - "Community 5"
Cohesion: 0.46
Nodes (7): build_plan(), content_pages(), default_wiki_path(), main(), parse_args(), title_key(), word_count()

### Community 6 - "Community 6"
Cohesion: 0.6
Nodes (4): check(), main(), missing_terms(), parse_args()

### Community 7 - "Community 7"
Cohesion: 1.0
Nodes (2): check(), main()

## Knowledge Gaps
- **Thin community `Community 7`** (3 nodes): `check()`, `main()`, `check_release_ready.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `lint()` connect `Community 0` to `Community 6`?**
  _High betweenness centrality (0.483) - this node is a cross-community bridge._
- **Why does `ingest()` connect `Community 1` to `Community 6`?**
  _High betweenness centrality (0.323) - this node is a cross-community bridge._
- **Why does `LintFixtureTests` connect `Community 0` to `Community 2`?**
  _High betweenness centrality (0.318) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `lint()` (e.g. with `.test_valid_fixture_has_no_lint_issues()` and `.test_archived_duplicate_does_not_make_active_link_ambiguous()`) actually correct?**
  _`lint()` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Should `Community 2` be split into smaller, more focused modules?**
  _Cohesion score 0.1 - nodes in this community are weakly interconnected._