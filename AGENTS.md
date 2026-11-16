Codex Agent Guide

Scope
- This file applies to the entire repository rooted at `.`. Follow these instructions
  for any files you modify within this repo.

Project Guidance
- Read the project's README.md for its structure, setup, and validation commands.
- Keep project-specific instructions in README.md and this shared guide
  independent of any particular project.

Coding/Writing Conventions
- Follow the project's formatter and linter configuration, including line length.
  Use a line length of 88 when the project does not specify one.
- Do not disable lint warnings
- Do not add license/copyright headers. Avoid one-letter variables.
- Prefer small, surgical patches that address the root cause.
- Characters: Use ASCII-only code and comments (plain keyboard characters). Allow
  Unicode only in string data read from inputs.
- Exceptions: Avoid broad handlers (no bare `except`, no `except Exception`). Catch
  specific types like `OSError`, `json.JSONDecodeError`, etc.
- Docstrings: Add a concise docstring to every module and public function. Discuss
  parameters and returns.

Writing conventions
- Always use American English.
- Never invent citations, affiliations, or disclosure details.
- Avoid library proxy URLs in references and links, including Stanford proxies.
  Use canonical DOI, publisher, or source URLs without institutional proxy wrappers.
- In Markdown and Latex source, preserve existing line breaks when editing.
  Write each new or rewritten sentence on its own source line, splitting long
  sentences at clause boundaries to stay within 88 characters per line.
- When writing text, assume you are making surgical (minimal) edits unless otherwise
  specified.
- Preserve existing comments unless asked to remove them.
- If you do not complete a todo, leave it in the text.
- When editing, keep the language you use as similar as possible to the original
  (diction, syntax, etc.). Often a "to do" direction will contain suitable language for
  an edit.
- When editing a section, generally you should not increase the length significantly
  unless absolutely necessary.
- Do not treat directives to make specific edits as a reason to dramatically alter the
  flow of a section.

Agent Workflow
- Plans: When tasks are multi-step or ambiguous, maintain an explicit, concise plan and
  update it as you progress.
- Preambles: Before running groups of commands, write a short (1-2 sentence) preamble.
- Reading code: Prefer `rg` for searching and read files in chunks of <=250 lines.
- File references in responses: Use inline code paths like `path/to/file.py:42`. Do not
  include ranges.
- Data hygiene: Avoid opening or processing very large files (e.g., `test.zip`) unless
  necessary.
- Scope discipline: Work within code/scripts unless the user requests data changes.

Sandbox, Approvals, and Safety
- Do not commit, push, or create git worktrees unless explicitly requested.
- If the filesystem is read-only or a command requires extra permissions, request
  escalation before writing or destructive actions.
- Avoid destructive commands (`rm`, `git reset`, etc.) unless the user explicitly asks.
- No network actions unless approved or permitted by the environment.

Validation
- If the project has runnable scripts, validate changes locally in a targeted way (run
  only what's necessary to verify the change).
- Do not fix unrelated issues or add new tooling unless asked. You may mention observed
  issues succinctly.

Communication Priorities
- Be concise, direct, and friendly.
- Propose next logical steps (e.g., run tests, add a helper) and ask before proceeding.
