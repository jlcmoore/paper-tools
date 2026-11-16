# paper-tools

Extract plain-text abstracts and prepare arXiv source archives from LaTeX papers.

## Usage

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and the
system tools for the command you need:

- Abstracts: `latexpand`, `pandoc`, and `iconv`.
- arXiv archives: `latexmk`, `pdflatex`, and `rsync`.

From a paper that uses this tool, run:

```sh
make abstract       # Print the abstract as one line of ASCII text.
make arxiv-clean    # Build and check arxiv_submission.zip.
```

The first run downloads the Python dependencies through `uvx`, which comes with uv.
Overleaf compilation does not need these tools.

## Add to a paper

Copy the settings and targets from [examples/Makefile](examples/Makefile).
Set `MAIN` to your main LaTeX filename without `.tex` and replace the example
`PAPER_TOOLS_REV` tag with a full commit hash.
Update that hash when you want to upgrade the tool.

Keep your cleaner settings in `arxiv_cleaner.yaml`.
Use `ARXIV_ARGS` for paper-specific options, for example:

```make
ARXIV_ARGS = --extra checklist.tex \
	--replace '\facctreviewtrue' '\facctreviewfalse'
```

Use `--source-dir DIR` to choose source directories; this replaces the defaults.
Run `uvx --from SOURCE paper-tools arxiv --help` for all options, replacing
`SOURCE` with the pinned Git URL from your Makefile.

## Development

Read [AGENTS.md](AGENTS.md) before editing.
Use Python 3.12, uv, and Node.js with npm.
The package runs on Python 3.9 or newer.

```sh
make init       # Install development dependencies from the lockfiles.
make pyfmt      # Format Python and sort imports.
make check      # Run lint, formatting, duplicate, ASCII, and test checks.
uv build        # Build a wheel and source archive.
```

To try a local checkout from a paper's directory:

```sh
make PAPER_TOOLS_SOURCE=../paper-tools abstract
```

When updating development dependencies, refresh and commit both lockfiles:

```sh
uv lock
npm install --package-lock-only --cache .npm-cache --no-audit --no-fund
```
