"""Verify the ASCII guard covers maintained files and skips generated content."""

import tempfile
import unittest
from pathlib import Path

from tools.check_ascii import find_non_ascii


class AsciiTests(unittest.TestCase):
    """Reject Unicode source while permitting external data in environments."""

    def test_non_ascii_source_reports_location(self):
        """Report the first non-ASCII byte's file, line, and column."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "source.py").write_text(
                "ASCII\nsmart" + chr(0x2014), encoding="utf-8"
            )
            self.assertEqual(find_non_ascii(root), ["source.py:2:6: non-ASCII content"])

    def test_generated_environment_is_excluded(self):
        """Installed dependencies can contain Unicode without hiding source errors."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "source.py").write_text("ASCII\n", encoding="utf-8")
            environment = root / ".venv"
            environment.mkdir()
            (environment / "external.txt").write_text(chr(0x2014), encoding="utf-8")
            self.assertEqual(find_non_ascii(root), [])


if __name__ == "__main__":
    unittest.main()
