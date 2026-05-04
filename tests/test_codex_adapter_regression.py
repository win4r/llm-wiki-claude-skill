import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LINT_SCRIPT = ROOT / "adapters" / "codex" / "scripts" / "llm_wiki_lint.py"
SCAFFOLD_SCRIPT = ROOT / "adapters" / "codex" / "scripts" / "llm_wiki_scaffold.py"
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


if __name__ == "__main__":
    unittest.main()
