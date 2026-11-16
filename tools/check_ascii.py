"""Reject non-ASCII bytes in maintained files, skipping generated directories."""

import os
import sys
from pathlib import Path

GENERATED_DIRECTORIES = frozenset(
    {
        ".git",
        ".npm-cache",
        ".pylint.d",
        ".ruff_cache",
        ".uv-cache",
        ".venv",
        "__pycache__",
        "dist",
        "node_modules",
    }
)


def find_non_ascii(root):
    """Return diagnostics for non-ASCII files under the Path root."""
    diagnostics = []
    for directory, subdirectories, filenames in os.walk(root):
        subdirectories[:] = sorted(
            name for name in subdirectories if name not in GENERATED_DIRECTORIES
        )
        for filename in sorted(filenames):
            path = Path(directory) / filename
            for line_number, line in enumerate(path.read_bytes().splitlines(), start=1):
                if line.isascii():
                    continue
                column = next(
                    index for index, value in enumerate(line, 1) if value > 127
                )
                diagnostics.append(
                    f"{path.relative_to(root)}:{line_number}:{column}: "
                    "non-ASCII content"
                )
                break
    return diagnostics


def main():
    """Check this repository; return one for violations or unreadable files."""
    try:
        diagnostics = find_non_ascii(Path(__file__).resolve().parents[1])
    except OSError as error:
        print(f"ASCII check failed: {error}", file=sys.stderr)
        return 1
    if diagnostics:
        print("\n".join(diagnostics), file=sys.stderr)
        return 1
    print("ASCII check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
