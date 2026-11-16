# paper-tools

A standalone package for the `abstract` and `arxiv-clean` Make targets used by
LaTeX paper repositories.
The implementation and tests live in this repository; each paper pins a tested
tool version in its Makefile.

## What a collaborator would do

`uvx` ships with uv and is shorthand for `uv tool run`.
It fetches and runs a Python command in an isolated, cached environment.
For example, `uvx --from SOURCE paper-tools abstract main.tex` runs the
`paper-tools` command supplied by the pinned package source.

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and the
system tools needed by the chosen command, clone or download a paper, then run:

```sh
make abstract
make arxiv-clean
```

The paper's Makefile runs `uvx --from SOURCE paper-tools ...`.
[uv's tool runner](https://docs.astral.sh/uv/guides/tools/) creates an isolated
environment and caches it for repeated runs.
There is no global Python package installation or sibling checkout requirement.
The package installs `arxiv-latex-cleaner==1.0.8` into that environment, so
packaging does not rely on a separately installed cleaner.
Abstract extraction needs `latexpand`, `pandoc`, and `iconv`.
arXiv packaging needs `latexmk`, `pdflatex`, and `rsync`.
The first invocation needs access to the tool source and its Python dependencies.
The Python dependencies are fetched even if that invocation only extracts an abstract.

These are local maintenance commands; ordinary Overleaf compilation does not
run the Makefile or need uv.

## What goes in each paper

[examples/Makefile](examples/Makefile) shows a complete integration.
The example uses the `v0.1.0` release tag for readability.
Use a full commit hash for `PAPER_TOOLS_REV` in each paper to keep its pin immutable:

```make
PAPER_TOOLS_REV = v0.1.0
PAPER_TOOLS_SOURCE = \
	git+https://github.com/jlcmoore/paper-tools@$(PAPER_TOOLS_REV)
PAPER_TOOLS = uvx --from "$(PAPER_TOOLS_SOURCE)" paper-tools

abstract:
	@$(PAPER_TOOLS) abstract "$(MAIN).tex"

arxiv-clean:
	@$(PAPER_TOOLS) arxiv "$(MAIN).tex" $(ARXIV_ARGS)
```

Keep the main filename and any paper-specific arguments in the paper Makefile.
The helper's default source directories are `sections`, `figures`, `tables`,
`shared`, `include`, `includes`, `img`, `manual_figures`, and `generated`.
It also includes root-level bibliography and LaTeX support files automatically.
Extra root-level inputs and a review toggle can be specified as follows:

```make
ARXIV_ARGS = --extra checklist.tex \
	--replace '\facctreviewtrue' '\facctreviewfalse'
```

Repeat `--source-dir DIR` to override the default directory list.
Other options include `--config PATH`, `--output PATH`, and `--extra PATH`.
The paper's `arxiv_cleaner.yaml` continues to define author comment commands.
No helper implementations, shared Make includes, tests, or sync commands need
to live in paper repositories after migration.

For a public tool repository, collaborators need no GitHub authentication.
For a private one, they need read access and Git credentials; access to an
Overleaf paper alone would not provide access to the tool repository.

## Pins and upgrades

A full Git commit pins the tool's own source.
An upgrade is an explicit edit to `PAPER_TOOLS_SOURCE`, followed by validation
and a normal commit in that paper.
Different papers can retain different tested versions.
Tags provide readable release names, but the full hash avoids a tag changing.
If the package is eventually published on PyPI, the equivalent source setting
would be `paper-tools==0.1.0`, using an actual published package name and version.

The cleaner's direct version is pinned, but its transitive Python dependencies
are resolved at installation time; uvx does not use a tool repository's uv.lock.
TeX packages, Pandoc, iconv, and rsync remain system dependencies.
This pins the workflow implementation, not a byte-for-byte PDF build environment.

The workflow fails on missing tools or files, command failures, missing/empty
abstracts, cleaned-source compilation failures, unresolved citations/references,
duplicate labels, and persistent rerun requests.
It restores newly built bibliographies, validates the cleaned copy with
pdfLaTeX, and atomically replaces the archive only after success.
Staging directories and logs are preserved for inspection.
Abstract extraction handles inline environments and section headings, strips
comments, expands includes, and produces one line of ASCII text.
It does not evaluate arbitrary TeX macros or conditional branches.

## Working on a local checkout

From a paper's directory, point uvx at this local source tree:

```sh
uvx --from ../paper-tools paper-tools --version
make -f ../paper-tools/examples/Makefile \
    PAPER_TOOLS_SOURCE=../paper-tools MAIN=acl_latex abstract
```

The Make command above suits `realistic-sim-overleaf`.
It uses the example Makefile without modifying the paper's existing Makefile.
A local directory is a development override, not a shared immutable pin.

Build an installable source archive and wheel:

```sh
uv build
```

For distribution testing, run uvx with the built wheel as its source.
The tests and development tooling live in this repository.
Paper repositories only need their Make targets, a commit pin, and their
paper-specific inputs and cleaner configuration.

## Development conventions and checks

Read [AGENTS.md](AGENTS.md) before editing.
Use Python 3.12 for development, uv, and Node.js with npm.
The runtime package supports Python 3.9 and newer.
The development environment is `.venv/`, created from `uv.lock`.
Keep both dependency lockfiles under version control.
Ruff and Pylint are pinned in `pyproject.toml`; jscpd is pinned in
`package.json` and `package-lock.json`.
The Node package contains development tools only and is not needed by collaborators
running the Python tool.

```sh
make init          # Install Python and Node development dependencies.
make pyfmt         # Organize imports and format Python with Ruff.
make check         # Run all checks and tests; stop on any failure.
```

Individual checks are `make ruff-check`, `make pylint`, `make jscpd`,
`make ascii`, and `make test`.
Ruff checks imports, formatting, errors, likely bugs, and modern Python conventions.
Pylint runs with its default warnings enabled and an 88-character line limit.
jscpd checks Python source, tests, and tools at a zero-duplication threshold,
using its normal minimum of five lines and 50 tokens per duplicated block.
The ASCII guard scans maintained files, including documentation and configuration,
while skipping generated environments, caches, and build output.
Unicode from external inputs is handled at runtime; test inputs use character
codes or escapes so checked-in files remain ASCII.
Do not add lint suppressions or weaken checks to hide findings.

Maintain the lockfiles when deliberately updating development dependencies:

```sh
uv lock
npm install --package-lock-only --cache .npm-cache --no-audit --no-fund
```

These development lockfiles do not change how a paper pins a released tool.
