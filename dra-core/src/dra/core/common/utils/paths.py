# Common path and file utilities

import os
from pathlib import Path, PosixPath
from typing import Optional

def cwd() -> Path:
    """Return the real path to the current working directory, which can be changed by an application!"""
    return Path(os.path.realpath('.'))

def this_files_directory(file: str|Path = __file__) -> Path:
    return Path(os.path.dirname(os.path.realpath(file)))

def resolve_path(path_str: str, possible_parent: Optional[Path], return_abs_path: bool = True) -> Path:
    """
    If the input `path_str` contains a directory prefix, then return it as a `Path`.
    If it doesn't contain a directory prefix, return a Path with `possible_parent` as
    the directory part.

    Args:
        path_str (str): A path that may or may not contain a directory prefix.
        possible_parent (Optional[Path]): If not None, use this parent path if `path_str` doesn't contain a directory prefix.
        return_abs_path (bool): Return the absolute path if the the resolved path is relative.

    Returns:
        The resolved path, whether or not it a actually exists!
    """
    path = Path(path_str)
    if not len(path.parents) or path.parents[0] == PosixPath('.'):
        if possible_parent:
            path = possible_parent / path
    
    if return_abs_path:
        return path.resolve()
    else:
        return path

def resolve_and_require_path(path_str: str, possible_parent: Optional[Path], return_abs_path: bool = True) -> Path:
    """
    Resolve a path and require it to exist. If it doesn't exist raise a `ValueError`.
    If the input `path_str` contains a directory prefix, then return it as a `Path`.
    If it doesn't contain a directory prefix, return a Path with `possible_parent` as
    the directory part.

    Args:
        path_str (str): A path that may or may not contain a directory prefix.
        possible_parent (Optional[Path]): If not None, use this parent path is `path_str` doesn't contain a directory prefix.
        return_abs_path (bool): Return the absolute path if the the resolved path is relative.

    Returns:
        The resolved path, but if it doesn't exist, raise a `ValueError`.
    """
    path = resolve_path(path_str, possible_parent, return_abs_path=return_abs_path)
    if not path.exists():
        raise ValueError(f"Resolved path '{path}' doesn't exist!")
    return path
