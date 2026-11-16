"""Regression tests for abstract extraction and arXiv packaging."""

import argparse
import contextlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from paper_tools import cli as paper
from paper_tools.cli import (
    _abstract,
    _arxiv,
    _extract_abstract,
    _run,
    _stage,
    _validate,
    _write_archive,
)


class CommandTests(unittest.TestCase):
    """Check directory selection through the installed command's parser."""

    def test_arxiv_defaults_include_common_source_directories(self):
        """An unconfigured paper stages its standard source directories."""
        with patch.object(paper, "_arxiv") as package:
            self.assertEqual(paper.main(["arxiv", "main.tex"]), 0)
        arguments = package.call_args.args[0]
        self.assertIn(Path("sections"), arguments.source_dir)
        self.assertIn(Path("generated"), arguments.source_dir)

    def test_explicit_directories_replace_defaults(self):
        """A paper can choose a custom source layout without copying helpers."""
        with patch.object(paper, "_arxiv") as package:
            self.assertEqual(
                paper.main(["arxiv", "main.tex", "--source-dir", "custom"]), 0
            )
        self.assertEqual(package.call_args.args[0].source_dir, [Path("custom")])


class AbstractTests(unittest.TestCase):
    """Check inline extraction, section fallback, and failure propagation."""

    def test_inline_and_multiline_environments(self):
        """Inline and multiline environments."""
        for content in ("One line.", "\nTwo\nlines.\n"):
            with self.subTest(content=content):
                source = r"\begin{abstract}" + content + r"\end{abstract}"
                self.assertEqual(_extract_abstract(source), content)

    def test_section_stops_before_body(self):
        """Section stops before body."""
        source = r"\section*{Abstract}Text.\section{Introduction}Body."
        self.assertEqual(_extract_abstract(source), "Text.")

    def test_bad_abstracts_fail(self):
        """Bad abstracts fail."""
        cases = [
            "No abstract",
            r"\begin{abstract}Unclosed",
            r"\begin{abstract} \end{abstract}",
            r"\begin{abstract}A\end{abstract}\begin{abstract}B\end{abstract}",
        ]
        for source in cases:
            with self.subTest(source=source), self.assertRaises(paper.WorkflowError):
                _extract_abstract(source)

    def test_command_failure_has_no_partial_abstract(self):
        """Command failure has no partial abstract."""
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "main.tex"
            source.touch()
            for stage in range(4):
                results = [r"\begin{abstract}Text\end{abstract}", "Text", "Text"][
                    :stage
                ]
                results.append(paper.WorkflowError("failed command"))
                with (
                    self.subTest(stage=stage),
                    patch.object(paper, "_require_tools"),
                    patch.object(paper, "_run", side_effect=results),
                    contextlib.redirect_stdout(io.StringIO()) as output,
                ):
                    with self.assertRaises(paper.WorkflowError):
                        _abstract(argparse.Namespace(source=source))
                    self.assertEqual(output.getvalue(), "")

    @unittest.skipUnless(
        all(shutil.which(tool) for tool in ("latexpand", "pandoc", "iconv")),
        "abstract tools are not installed",
    )
    def test_real_tools_handle_comments_quotes_and_macro_inputs(self):
        """Real tools handle comments quotes and macro inputs."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            abstract = root / "content.tex"
            abstract.write_text(
                "A 50\\% result with ``quotes.'' % hidden\n", encoding="utf-8"
            )
            source = root / "main.tex"
            source.write_text(
                "% \\begin{abstract}commented out\\end{abstract}\n"
                + r"\begin{abstract}\input{"
                + str(abstract)
                + r"}\end{abstract}"
                + "\n"
                + r"\newcommand{\example}[1]{\input{#1}}",
                encoding="utf-8",
            )
            script = Path(paper.__file__).resolve()
            result = subprocess.run(
                [sys.executable, str(script), "abstract", str(source)],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, 'A 50% result with "quotes."\n')
            abstract.unlink()
            result = subprocess.run(
                [sys.executable, str(script), "abstract", str(source)],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")


class PackagingTests(unittest.TestCase):
    """Verify archive integrity and rejection of incomplete submissions."""

    def setUp(self):
        """Create isolated paths for each test and register their cleanup."""
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        self.cleaned = self.root / "cleaned"
        self.cleaned.mkdir()
        (self.cleaned / "main.tex").write_text("source", encoding="utf-8")
        (self.cleaned / "main.bbl").write_text("bibliography", encoding="utf-8")
        self.output = self.root / "existing.zip"
        self.output.write_bytes(b"previous archive")

    def test_archive_has_sources_at_root(self):
        """Archive has sources at root."""
        _write_archive(self.cleaned, self.output)
        with zipfile.ZipFile(self.output) as archive:
            self.assertEqual(set(archive.namelist()), {"main.tex", "main.bbl"})
            self.assertIsNone(archive.testzip())

    def test_zip_failure_preserves_existing_archive(self):
        """Zip failure preserves existing archive."""
        with (
            patch.object(zipfile.ZipFile, "write", side_effect=OSError("disk full")),
            self.assertRaises(OSError),
        ):
            _write_archive(self.cleaned, self.output)
        self.assertEqual(self.output.read_bytes(), b"previous archive")
        self.assertEqual(list(self.root.glob(".existing.zip.*")), [])

    def test_warning_only_errors_fail_validation(self):
        """Warning only errors fail validation."""
        warnings = [
            "LaTeX Warning: There were undefined references.",
            "Package natbib Warning: There were undefined citations.",
            "LaTeX Warning: Reference `missing' on page 1 undefined on input line 4.",
            "Package natbib Warning: Citation `missing' on page 1 undefined",
            "LaTeX Warning: Label `duplicate' multiply defined.",
            "LaTeX Warning: There were multiply-defined labels.",
            "No file main.bbl.",
            "Package biblatex Warning: Please (re)run Biber on the file:",
        ]
        for warning in warnings:
            with self.subTest(warning=warning):
                staging = self.root / str(warnings.index(warning))
                staging.mkdir()
                with (
                    patch.object(paper, "_run", side_effect=self._log_writer(warning)),
                    self.assertRaises(paper.WorkflowError),
                ):
                    _validate(Path("main.tex"), self.cleaned, staging)

    def _log_writer(self, warning):
        def write_log(_command, *, cwd, **_options):
            (cwd / "main.log").write_text(warning, encoding="utf-8")
            return ""

        return write_log

    def test_references_can_settle_after_three_passes(self):
        """References can settle after three passes."""
        calls = []

        def compile_source(command, *, cwd, **_options):
            calls.append(command)
            message = "Label(s) may have changed." if len(calls) < 3 else "OK"
            (cwd / "main.log").write_text(message, encoding="utf-8")
            return ""

        with patch.object(paper, "_run", side_effect=compile_source):
            _validate(Path("main.tex"), self.cleaned, self.root)
        self.assertEqual(len(calls), 3)

    def test_persistent_rerun_fails(self):
        """Persistent rerun fails."""
        with (
            patch.object(paper, "_run", side_effect=self._log_writer("Rerun to get")),
            self.assertRaisesRegex(paper.WorkflowError, "did not stabilize"),
        ):
            _validate(Path("main.tex"), self.cleaned, self.root)

    def test_failed_build_or_cleaner_cannot_replace_archive(self):
        """Failed build or cleaner cannot replace archive."""
        for failed_command in ("latexmk", "arxiv_latex_cleaner"):
            with self.subTest(command=failed_command):
                args = argparse.Namespace(
                    source=Path(__file__), config=Path(__file__), output=self.output
                )
                staging = self.root / failed_command
                staging.mkdir()

                def run_command(command, *, expected=failed_command, **_options):
                    if command[0] == expected:
                        raise paper.WorkflowError("command failed")
                    return ""

                with (
                    patch.object(paper, "_require_tools"),
                    patch.object(paper.tempfile, "mkdtemp", return_value=str(staging)),
                    patch.object(paper, "_stage"),
                    patch.object(paper, "_run", side_effect=run_command),
                    self.assertRaises(paper.WorkflowError),
                ):
                    _arxiv(args)
                self.assertEqual(self.output.read_bytes(), b"previous archive")

    @unittest.skipUnless(shutil.which("rsync"), "rsync is not installed")
    def test_staging_drops_stale_builds_and_includes_new_support_files(self):
        """Staging drops stale builds and includes new support files."""
        repo = self.root / "repo"
        repo.mkdir()
        (repo / "main.tex").write_text(r"\reviewtrue", encoding="utf-8")
        (repo / "new.sty").touch()
        (repo / "main.bbl").write_text("stale", encoding="utf-8")
        (repo / "sections").mkdir()
        (repo / "sections" / "section.tex").touch()
        (repo / "sections" / "section.aux").touch()
        (repo / "private.txt").touch()
        (repo / "extra input.tex").touch()
        work = self.root / "work"
        work.mkdir()
        args = argparse.Namespace(
            source=Path("main.tex"),
            source_dir=[Path("sections"), Path("absent")],
            extra=[Path("extra input.tex")],
            replace=[(r"\reviewtrue", r"\reviewfalse")],
        )
        previous = Path.cwd()
        try:
            os.chdir(repo)
            _stage(args, work, self.root)
        finally:
            os.chdir(previous)
        files = {
            str(path.relative_to(work)) for path in work.rglob("*") if path.is_file()
        }
        self.assertEqual(
            files, {"main.tex", "new.sty", "sections/section.tex", "extra input.tex"}
        )
        self.assertEqual((repo / "main.tex").read_text(), r"\reviewtrue")
        self.assertEqual((work / "main.tex").read_text(), r"\reviewfalse")

    def test_subprocess_failure_is_reported(self):
        """Subprocess failure is reported."""
        with self.assertRaisesRegex(paper.WorkflowError, "exit 7"):
            _run([sys.executable, "-c", "import sys; sys.exit(7)"])


if __name__ == "__main__":
    unittest.main()
