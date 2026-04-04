# Unit tests for the "path utils" module using Hypothesis for property-based testing.
# https://hypothesis.readthedocs.io/en/latest/

from hypothesis import given, strategies as st
import unittest
from pathlib import Path, PosixPath
import os

from tests.dra.utils import (
    parent_path_text,
    no_slash_nonempty_text,
    no_leading_dots,
)
from dra.core.common.utils.paths import cwd, this_files_directory, resolve_path, resolve_and_require_path

class TestPathUtils(unittest.TestCase):
    """
    Test the path- and file-related utilities.
    """

    def test_cwd_returns_the_current_working_directory(self):
        self.assertEqual(str(os.path.realpath(PosixPath('.'))), str(cwd()))

    def test_this_files_directory_returns_the_directory_for_a_file(self):
        actual = this_files_directory()
        # `cwd()` resolves to `src`, the parent of the `common` directory where this file exists.
        expected = cwd() / 'src/dra/core/common/utils'
        self.assertEqual(str(expected), str(actual), f"expected: {expected}, actual: {actual}")

    @given(parent_path_text(), no_leading_dots())
    def test_resolve_path_adds_missing_parents_directory(self, parents: str, file: str):
        actual = resolve_path(file, Path(parents), return_abs_path=False)
        expected = Path(os.path.join(parents, file))
        self.assertEqual(expected, actual)

    @given(parent_path_text(), no_leading_dots())
    def test_resolve_path_does_not_add_parents_directory_if_it_already_has_parents(self, parents: str, file: str):
        file = f"{parents}/{file}"
        actual = resolve_path(file, Path(parents), return_abs_path=False)
        expected = Path(file)
        self.assertEqual(expected, actual, f"file: {file}, actual: {actual}, expected: {expected}")

    def test_resolve_path_returns_absolute_path_by_default(self):
        file = "README.md"
        parent = Path("..")  # relative to to the "src" directory!
        actual = resolve_path(file, Path(parent))
        expected = Path(parent / file).resolve()
        self.assertEqual(expected, actual, f"file: {file}, actual: {actual}, expected: {expected}")

    def test_resolve_and_require_path_returns_absolute_path_by_default(self):
        file = "README.md"
        parent = Path("..")  # relative to to the "src" directory!
        actual = resolve_and_require_path(file, parent)
        expected = Path(parent / file).resolve()
        self.assertEqual(expected, actual, f"file: {file}, actual: {actual}, expected: {expected}")

    @given(parent_path_text(), no_leading_dots())
    def test_resolve_and_require_path_raises_for_nonexistent_path(self, parents: str, file: str):
        file = f"{parents}/{file}"
        with self.assertRaises(ValueError):
            actual = resolve_and_require_path(file, Path(parents))

if __name__ == "__main__":
    unittest.main()