import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LINT_SCRIPT = ROOT / "adapters" / "codex" / "scripts" / "llm_wiki_lint.py"
SCAFFOLD_SCRIPT = ROOT / "adapters" / "codex" / "scripts" / "llm_wiki_scaffold.py"
INGEST_SCRIPT = ROOT / "adapters" / "codex" / "scripts" / "llm_wiki_ingest_arxiv.py"
REPAIR_SCRIPT = ROOT / "adapters" / "codex" / "scripts" / "llm_wiki_repair.py"
COMPILE_PLAN_SCRIPT = ROOT / "adapters" / "codex" / "scripts" / "llm_wiki_compile_plan.py"
PARITY_SCRIPT = ROOT / "adapters" / "codex" / "scripts" / "llm_wiki_adapter_parity.py"
RELEASE_CHECK_SCRIPT = ROOT / "scripts" / "check_release_ready.py"
FIXTURES = ROOT / "tests" / "fixtures"


def load_lint_module():
    spec = importlib.util.spec_from_file_location("llm_wiki_lint", LINT_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class LintFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lint_module = load_lint_module()

    def test_valid_fixture_has_no_lint_issues(self):
        issues, page_count = self.lint_module.lint(FIXTURES / "valid-wiki")

        self.assertEqual(page_count, 2)
        non_empty = {key: value for key, value in issues.items() if value}
        self.assertEqual(non_empty, {})

    def test_archived_duplicate_does_not_make_active_link_ambiguous(self):
        issues, _ = self.lint_module.lint(FIXTURES / "valid-wiki")

        self.assertEqual(issues["ambiguous_links"], [])
        self.assertEqual(issues["broken_links"], [])

    def test_broken_fixture_reports_expected_categories(self):
        issues, page_count = self.lint_module.lint(FIXTURES / "broken-wiki")

        self.assertEqual(page_count, 1)
        for category in (
            "unknown_tags",
            "missing_sources",
            "broken_links",
            "low_outbound_links",
            "orphans",
            "not_indexed",
        ):
            self.assertGreater(len(issues[category]), 0, category)


class LintCliTests(unittest.TestCase):
    def test_strict_cli_passes_for_valid_fixture(self):
        result = subprocess.run(
            [sys.executable, str(LINT_SCRIPT), "--wiki", str(FIXTURES / "valid-wiki"), "--strict"],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Status: OK", result.stdout)

    def test_strict_cli_fails_for_broken_fixture(self):
        result = subprocess.run(
            [sys.executable, str(LINT_SCRIPT), "--wiki", str(FIXTURES / "broken-wiki"), "--strict"],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Status: ISSUES FOUND", result.stdout)
        self.assertIn("broken_links", result.stdout)

    def test_json_report_is_machine_readable(self):
        result = subprocess.run(
            [sys.executable, str(LINT_SCRIPT), "--wiki", str(FIXTURES / "valid-wiki"), "--json", "--strict"],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "ok")
        self.assertEqual(report["total_issues"], 0)

    def test_boundary_fixture_reports_case_mismatch(self):
        result = subprocess.run(
            [sys.executable, str(LINT_SCRIPT), "--wiki", str(FIXTURES / "boundary-wiki"), "--json"],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertGreater(len(report["issues"]["case_mismatch_links"]), 0)
        self.assertEqual(report["issues"]["broken_links"], [])


class ScaffoldRegressionTests(unittest.TestCase):
    def test_scaffold_creates_lint_clean_empty_wiki(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            wiki = Path(tmpdir) / "sample-wiki"
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCAFFOLD_SCRIPT),
                    "--wiki",
                    str(wiki),
                    "--domain",
                    "Regression fixture",
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue((wiki / "SCHEMA.md").exists())
            self.assertTrue((wiki / "index.md").exists())
            self.assertTrue((wiki / "log").is_dir())
            self.assertTrue((wiki / "raw" / "articles").is_dir())
            self.assertFalse((Path(tmpdir) / "README.md").exists())

            lint_result = subprocess.run(
                [sys.executable, str(LINT_SCRIPT), "--wiki", str(wiki), "--strict"],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(lint_result.returncode, 0, lint_result.stdout + lint_result.stderr)

    def test_scaffold_preserves_existing_schema_without_force(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            wiki = Path(tmpdir) / "sample-wiki"
            wiki.mkdir()
            schema = wiki / "SCHEMA.md"
            schema.write_text("# Existing Schema\n", encoding="utf-8")

            subprocess.run(
                [sys.executable, str(SCAFFOLD_SCRIPT), "--wiki", str(wiki)],
                text=True,
                capture_output=True,
                check=True,
            )

            self.assertEqual(schema.read_text(encoding="utf-8"), "# Existing Schema\n")

    def test_scaffold_container_readme_always_mode(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            wiki = Path(tmpdir) / "container" / "sample-wiki"
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCAFFOLD_SCRIPT),
                    "--wiki",
                    str(wiki),
                    "--container-readme",
                    "always",
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue((wiki.parent / "README.md").exists())


class ArxivIngestE2ETests(unittest.TestCase):
    def test_arxiv_ingest_dry_run_and_apply_are_lint_clean(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            wiki = Path(tmpdir) / "wiki"
            shutil.copytree(FIXTURES / "valid-wiki", wiki)
            metadata = FIXTURES / "arxiv" / "toolformer.atom"

            dry_run = subprocess.run(
                [
                    sys.executable,
                    str(INGEST_SCRIPT),
                    "--wiki",
                    str(wiki),
                    "--metadata-file",
                    str(metadata),
                    "--dry-run",
                    "--json",
                    "--today",
                    "2026-05-03",
                    "--now",
                    "10:11",
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(dry_run.returncode, 0, dry_run.stdout + dry_run.stderr)
            plan = json.loads(dry_run.stdout)
            self.assertEqual(plan["created"][0]["arxiv_id"], "2302.04761")

            applied = subprocess.run(
                [
                    sys.executable,
                    str(INGEST_SCRIPT),
                    "--wiki",
                    str(wiki),
                    "--metadata-file",
                    str(metadata),
                    "--json",
                    "--today",
                    "2026-05-03",
                    "--now",
                    "10:11",
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)
            applied_plan = json.loads(applied.stdout)
            page_rel = applied_plan["created"][0]["writes"][1]["path"]
            raw_rel = applied_plan["created"][0]["writes"][0]["path"]
            self.assertTrue((wiki / page_rel).exists())
            self.assertTrue((wiki / raw_rel).exists())
            self.assertIn("[[toolformer-language-models-can-teach-themselves-to-use-tools]]", (wiki / "index.md").read_text())
            self.assertIn("arXiv batch", (wiki / "log" / "20260503.md").read_text())

            lint_result = subprocess.run(
                [sys.executable, str(LINT_SCRIPT), "--wiki", str(wiki), "--strict"],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(lint_result.returncode, 0, lint_result.stdout + lint_result.stderr)

            duplicate = subprocess.run(
                [
                    sys.executable,
                    str(INGEST_SCRIPT),
                    "--wiki",
                    str(wiki),
                    "--metadata-file",
                    str(metadata),
                    "--json",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            duplicate_plan = json.loads(duplicate.stdout)
            self.assertEqual(duplicate_plan["skipped"][0]["arxiv_id"], "2302.04761")


class RepairRegressionTests(unittest.TestCase):
    def test_repair_migrates_paper_type_and_missing_sources(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            wiki = Path(tmpdir) / "wiki"
            shutil.copytree(FIXTURES / "valid-wiki", wiki)
            drift = wiki / "concepts" / "drift.md"
            drift.write_text(
                """---
title: Drift
created: 2026-05-03
updated: 2026-05-03
type: paper
tags: [research]
---

# Drift

Drift links to [[alpha]] and [[beta]].
""",
                encoding="utf-8",
            )
            with (wiki / "index.md").open("a", encoding="utf-8") as handle:
                handle.write("- [[drift]] - Drift page\n")

            result = subprocess.run(
                [sys.executable, str(REPAIR_SCRIPT), "--wiki", str(wiki), "--apply", "--json"],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(len(report["changes"]), 1)
            repaired = drift.read_text(encoding="utf-8")
            self.assertIn("type: summary", repaired)
            self.assertIn("sources: [raw/refs/concepts-drift-source-needed.md]", repaired)
            self.assertTrue((wiki / "raw" / "refs" / "concepts-drift-source-needed.md").exists())

            lint_result = subprocess.run(
                [sys.executable, str(LINT_SCRIPT), "--wiki", str(wiki), "--strict"],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(lint_result.returncode, 0, lint_result.stdout + lint_result.stderr)


class CompilePlanTests(unittest.TestCase):
    def test_compile_plan_detects_oversized_and_not_indexed_pages(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            wiki = Path(tmpdir) / "wiki"
            shutil.copytree(FIXTURES / "valid-wiki", wiki)
            large = wiki / "concepts" / "large-topic.md"
            large.write_text(
                """---
title: Large Topic
created: 2026-05-03
updated: 2026-05-03
type: concept
tags: [research]
sources: [raw/articles/source-a.md]
---

# Large Topic

[[alpha]] [[beta]]

"""
                + " ".join(["word"] * 40),
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, str(COMPILE_PLAN_SCRIPT), "--wiki", str(wiki), "--max-words", "20", "--json"],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            plan = json.loads(result.stdout)
            self.assertTrue(plan["needs_compile"])
            self.assertEqual(plan["oversized_pages"][0]["path"], "concepts/large-topic.md")
            self.assertIn("concepts/large-topic/index.md", plan["oversized_pages"][0]["suggestion"])
            self.assertNotIn(str(tmpdir), plan["oversized_pages"][0]["suggestion"])
            self.assertIn("concepts/large-topic.md", plan["not_indexed"])


class ParityAndReleaseTests(unittest.TestCase):
    def test_adapter_parity_passes(self):
        result = subprocess.run(
            [sys.executable, str(PARITY_SCRIPT), "--root", str(ROOT), "--json"],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(json.loads(result.stdout)["ok"])

    def test_release_ready_passes(self):
        result = subprocess.run(
            [sys.executable, str(RELEASE_CHECK_SCRIPT)],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(json.loads(result.stdout)["ok"])


if __name__ == "__main__":
    unittest.main()
