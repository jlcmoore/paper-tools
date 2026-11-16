"""Extract plain-text abstracts and build validated arXiv source archives."""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import zipfile
from pathlib import Path

DEFAULT_SOURCE_DIRS = (
    "sections",
    "figures",
    "tables",
    "shared",
    "include",
    "includes",
    "img",
    "manual_figures",
    "generated",
)
SUPPORT_SUFFIXES = (
    ".bib",
    ".bst",
    ".sty",
    ".cls",
    ".bbx",
    ".cbx",
    ".dbx",
    ".def",
    ".cfg",
    ".clo",
)
BUILD_PATTERNS = (
    "*.aux",
    "*.bbl",
    "*.blg",
    "*.fdb_latexmk",
    "*.fls",
    "*.log",
    "*.out",
    "*.synctex.gz",
    "*.toc",
    "*.nav",
    "*.snm",
)
BAD_REFERENCES = re.compile(
    r"There were undefined (?:references|citations)"
    r"|(?:Reference|Citation) [^\n]* undefined"
    r"|There were multiply[- ]defined labels"
    r"|Label [^\n]* multiply defined"
    r"|No file [^\n]*\.bbl"
    r"|Please \(re\)run Biber",
    re.IGNORECASE,
)
RERUN = re.compile(
    r"Label\(s\) may have changed|Rerun to get|Please rerun LaTeX",
    re.IGNORECASE,
)


class WorkflowError(RuntimeError):
    """Report a workflow failure without a Python traceback."""


def _require_tools(*names):
    """Raise WorkflowError if any named command is missing from PATH."""
    missing = [name for name in names if shutil.which(name) is None]
    if missing:
        raise WorkflowError("Required command(s) not found: " + ", ".join(missing))


def _require_file(path):
    """Raise WorkflowError if path is not an existing file."""
    if not path.is_file():
        raise WorkflowError(f"File not found: {path}")


def _run(command, *, cwd=None, input_text=None, log=None):
    """Run command and return stdout, raising WorkflowError on failure.

    Optionally set cwd, send input_text to stdin, and save output to log.
    """
    result = subprocess.run(
        command,
        cwd=cwd,
        input=input_text,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    if log is not None:
        log.write_text(result.stdout + result.stderr, encoding="utf-8")
    if result.returncode:
        detail = f"; see {log}" if log is not None else ""
        diagnostic = (result.stdout + result.stderr)[-6000:]
        raise WorkflowError(
            f"{command[0]} failed (exit {result.returncode}){detail}\n{diagnostic}"
        )
    if result.stderr and log is None:
        print(result.stderr, file=sys.stderr, end="")
    return result.stdout


def _extract_abstract(expanded):
    """Return abstract text from expanded LaTeX, rejecting missing or empty text."""
    starts = list(re.finditer(r"\\begin\s*\{abstract\}", expanded))
    if starts:
        if len(starts) != 1:
            raise WorkflowError("Found multiple abstract environments.")
        ending = re.search(r"\\end\s*\{abstract\}", expanded[starts[0].end() :])
        if ending is None:
            raise WorkflowError("Abstract environment has no closing \\end{abstract}.")
        content = expanded[starts[0].end() : starts[0].end() + ending.start()]
    else:
        heading = re.search(r"\\section\*?\s*\{[Aa]bstract\}", expanded)
        if heading is None:
            raise WorkflowError("Could not find an abstract environment or section.")
        content = re.split(
            r"\\(?:section\*?\s*\{|end\s*\{document\}|bibliography\s*\{)",
            expanded[heading.end() :],
            maxsplit=1,
        )[0]
    if not content.strip():
        raise WorkflowError("Abstract is empty.")
    return content


def _abstract(args):
    """Extract the abstract from args.source and print one ASCII line."""
    _require_tools("latexpand", "pandoc", "iconv")
    _require_file(args.source)
    unexpanded = _run(["latexpand", "--keep-includes", str(args.source)])
    if re.search(r"\\begin\s*\{abstract\}|\\section\*?\s*\{[Aa]bstract\}", unexpanded):
        content = _extract_abstract(unexpanded)
        # Expand only the abstract to avoid interpreting \input{#1} in body macros.
        with tempfile.TemporaryDirectory(prefix="abstract.") as directory:
            extract = Path(directory) / "abstract.tex"
            extract.write_text(content, encoding="utf-8")
            content = _run(["latexpand", "--fatal", str(extract)])
    else:
        expanded = _run(["latexpand", "--fatal", str(args.source)])
        content = _extract_abstract(expanded)
    plain = _run(["pandoc", "-f", "latex", "-t", "plain"], input_text=content)
    # macOS iconv flags smart quotes as invalid even when it transliterates them.
    punctuation = {
        0x2018: "'",
        0x2019: "'",
        0x201C: '"',
        0x201D: '"',
        0x2010: "-",
        0x2011: "-",
        0x2013: "-",
        0x2014: "--",
        0x2026: "...",
    }
    normalized = unicodedata.normalize("NFKD", plain.translate(punctuation))
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    ascii_text = _run(
        ["iconv", "-f", "UTF-8", "-t", "ASCII//TRANSLIT"],
        input_text=normalized,
    )
    single_line = " ".join(ascii_text.split())
    if not single_line:
        raise WorkflowError("Abstract converted to empty plain text.")
    if not single_line.isascii():
        raise WorkflowError("Abstract could not be converted to ASCII.")
    print(single_line)


def _relative_path(value):
    """Return value as a Path, rejecting absolute paths and parent traversal."""
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or path == Path("."):
        raise argparse.ArgumentTypeError(
            f"Expected a repository-relative path: {value}"
        )
    return path


def _stage(args, work_dir, temp_root):
    """Copy sources to work_dir, apply args.replace, and save logs in temp_root."""
    includes = [args.source]
    includes.extend(
        path
        for path in Path(".").iterdir()
        if path.is_file() and path.suffix in SUPPORT_SUFFIXES
    )
    includes.extend(path for path in args.source_dir if path.is_dir())
    for extra in args.extra:
        _require_file(extra)
        includes.append(extra)
    command = ["rsync", "-a", "--copy-links", "--prune-empty-dirs"]
    for pattern in (".git", ".gitkeep", ".DS_Store", *BUILD_PATTERNS):
        command.append(f"--exclude={pattern}")
    # Explicit parent rules let MAIN and extra files live in subdirectories.
    for path in sorted(set(includes)):
        for parent in reversed(path.parents):
            if parent != Path("."):
                command.append(f"--include=/{parent.as_posix()}/")
        suffix = "/***" if path.is_dir() else ""
        command.append(f"--include=/{path.as_posix()}{suffix}")
    command.extend(["--exclude=*", "./", str(work_dir) + "/"])
    _run(command, log=temp_root / "stage.log")
    staged_main = work_dir / args.source
    for old, new in args.replace:
        text = staged_main.read_text(encoding="utf-8")
        if old not in text:
            raise WorkflowError(
                f"Staging replacement not found in {args.source}: {old}"
            )
        staged_main.write_text(text.replace(old, new), encoding="utf-8")


def _check_references(log):
    """Return log text, raising WorkflowError for reference or bibliography errors."""
    text = log.read_text(encoding="utf-8", errors="replace")
    matches = [
        line.strip() for line in text.splitlines() if BAD_REFERENCES.search(line)
    ]
    if matches:
        raise WorkflowError(
            f"Unresolved citations/references or duplicate labels in {log}:\n"
            + "\n".join(matches[:20])
        )
    return text


def _validate(source, cleaned_dir, temp_root):
    """Check source compiles from cleaned_dir; keep build files in temp_root."""
    validate_dir = temp_root / "validate"
    shutil.copytree(cleaned_dir, validate_dir)
    print("Validating cleaned arXiv source with pdflatex", flush=True)
    # Use only the shipped .bbl, never BibTeX or the original build's aux files.
    command = [
        "pdflatex",
        "-interaction=nonstopmode",
        "-halt-on-error",
        "-recorder",
        "-no-parse-first-line",
        "-file-line-error",
        str(source),
    ]
    log = validate_dir / (source.stem + ".log")
    for pass_number in range(1, 6):
        _run(command, cwd=validate_dir, log=temp_root / f"validate-{pass_number}.log")
        text = log.read_text(encoding="utf-8", errors="replace")
        if pass_number >= 2 and not RERUN.search(text):
            _check_references(log)
            return
    _check_references(log)
    raise WorkflowError(f"Cleaned source did not stabilize after 5 passes; see {log}")


def _write_archive(cleaned_dir, output):
    """Zip cleaned_dir into output, preserving any old archive on failure."""
    # Create beside the destination so os.replace is atomic across filesystems.
    with tempfile.NamedTemporaryFile(
        prefix=f".{output.name}.",
        suffix=".tmp",
        dir=output.parent,
        delete=False,
    ) as temporary:
        temporary_path = Path(temporary.name)
    try:
        with zipfile.ZipFile(temporary_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(cleaned_dir.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(cleaned_dir))
        os.replace(temporary_path, output)
    finally:
        temporary_path.unlink(missing_ok=True)


def _arxiv(args):
    """Build, clean, and validate args.source before writing args.output."""
    _require_tools("arxiv_latex_cleaner", "latexmk", "pdflatex", "rsync")
    _require_file(args.source)
    _require_file(args.config)
    output = args.output.absolute()
    if not output.parent.is_dir():
        raise WorkflowError(f"Output directory not found: {output.parent}")
    temp_root = Path(tempfile.mkdtemp(prefix="arxiv_cleaner."))
    print(f"Preserving staging directory: {temp_root}", flush=True)
    work_dir = temp_root / "repo"
    work_dir.mkdir()
    _stage(args, work_dir, temp_root)
    _run(
        [
            "latexmk",
            "-pdf",
            "-interaction=nonstopmode",
            "-halt-on-error",
            str(args.source),
        ],
        cwd=work_dir,
        log=temp_root / "build.log",
    )
    _run(
        [
            "arxiv_latex_cleaner",
            str(work_dir),
            "--config",
            str(args.config.resolve()),
            "--keep_bib",
        ],
        log=temp_root / "cleaner.log",
    )
    cleaned_dir = temp_root / "repo_arXiv"
    if not cleaned_dir.is_dir():
        raise WorkflowError(f"Cleaned output directory not found: {cleaned_dir}")
    # Restore fresh bibliography output even when cleaner versions discard it.
    for bibliography in work_dir.rglob("*.bbl"):
        destination = cleaned_dir / bibliography.relative_to(work_dir)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(bibliography, destination)
    _validate(args.source, cleaned_dir, temp_root)
    _write_archive(cleaned_dir, output)
    print(f"Wrote {output}")


def main(argv=None):
    """Run argv (or process arguments when omitted); return an exit status."""
    parser = argparse.ArgumentParser(prog="paper-tools", description=__doc__)
    parser.add_argument("--version", action="version", version="%(prog)s 0.1.0")
    subparsers = parser.add_subparsers(dest="command", required=True)
    abstract = subparsers.add_parser("abstract", help="Print one ASCII abstract line")
    abstract.add_argument("source", type=Path)
    abstract.set_defaults(run=_abstract)
    arxiv = subparsers.add_parser("arxiv", help="Build and validate a source archive")
    arxiv.add_argument("source", type=_relative_path)
    arxiv.add_argument("--config", type=Path, default=Path("arxiv_cleaner.yaml"))
    arxiv.add_argument("--output", type=Path, default=Path("arxiv_submission.zip"))
    arxiv.add_argument(
        "--source-dir",
        type=_relative_path,
        action="append",
        help="Override default source directories; repeat for each directory",
    )
    arxiv.add_argument("--extra", type=_relative_path, action="append", default=[])
    arxiv.add_argument("--replace", nargs=2, action="append", default=[])
    arxiv.set_defaults(run=_arxiv)
    args = parser.parse_args(argv)
    if args.command == "arxiv" and args.source_dir is None:
        args.source_dir = [Path(directory) for directory in DEFAULT_SOURCE_DIRS]
    try:
        args.run(args)
    except (WorkflowError, OSError, zipfile.BadZipFile) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
