# Agent Guide

## Scope and project guidance

- This guide applies to the entire repository.
- Read `README.md` before editing; it documents setup, structure, and validation.
- Keep project-specific setup details in `README.md` and this guide general.

## Coding and writing conventions

- Use American English in documentation, comments, and user-facing messages.
- Use ASCII-only source, comments, documentation, and configuration.
  Unicode may occur in external input data; normalize it at input/output boundaries.
  Express Unicode test input with escapes or character codes in source files.
- Follow the formatter and lint configuration; keep lines within 88 characters.
- Keep imports alphabetized and grouped into standard library, third-party,
  and local imports, using Ruff's import formatter.
- Add concise docstrings to every module and public function.
  Describe parameters and return values where relevant.
- Catch specific exception types; do not use bare `except` or `except Exception`.
- Prefer small, focused changes that fix the cause of an issue.
- Look for shared logic before adding duplicated code.
- Use descriptive names; avoid one-letter variables.
- Do not add license or copyright headers, environment shebangs, lint suppression
  comments, type-ignore comments, or pragma comments.
- Do not disable Ruff or Pylint warnings or exclude maintained code from checks
  to hide failures.
- Preserve existing comments and relevant TODOs.
- Preserve existing Markdown line breaks when possible.
  Write each new prose sentence on its own source line, wrapping at clauses.

## Formatting and validation

- Use the repository's pinned development tools and documented environment.
- Format and organize Python code with Ruff.
- Run Ruff lint and formatting checks, Pylint, jscpd duplicate detection,
  the ASCII check, and relevant tests before finishing code changes.
- Treat a nonzero check status as a failure; do not mask it in shell recipes.
- Fix findings without weakening rules, raising duplication thresholds,
  or adding unnecessary abstractions merely to satisfy a checker.
- If a finding cannot be fixed within scope, report it and its effect honestly.
- Keep generated environments, caches, reports, and build artifacts out of Git.

## Agent workflow

- For multistep work, state a concise plan and keep progress updates current.
- Before a group of commands, explain its purpose briefly.
- Prefer `rg` for searching and read source in chunks of at most 250 lines.
- Make minimal edits and avoid unrelated paper or data changes.
- Run targeted checks appropriate to the change; broaden only when needed.
- Do not open large archives or generated data unless the task requires it.
- Do not commit, push, publish packages, or create Git worktrees unless explicitly
  requested or otherwise authorized in the conversation.
- Request sandbox escalation when necessary and explain any remaining blocker.
- Keep user-facing updates concise and distinguish verified results from assumptions.
