"""
"MarkdownElements" represent major sections of a markdown document, like sections, tables, etc.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import re
import sys
import time
from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

from mcp_agent.workflows.deep_orchestrator.orchestrator import DeepOrchestrator
from mcp_agent.workflows.deep_orchestrator.config import DeepOrchestratorConfig

from dra.core.common.utils.strings import to_id

class MarkdownElement():
    """Super type of the other markdown-related types.
    Note: There are places in subtype method signatures where `MarkdownElement`
    is used, but really the type itself should be used. It appears that Python
    doesn't allow self-references to a type _while inside_ its definition!
    """
    def __init__(self, title: str = ''):
        self.title = title

    def __repr__(self) -> str:
        return self.title

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, MarkdownElement):
            return False
        return self.title == other.title

class MarkdownSection(MarkdownElement):
    def __init__(self, 
        title: str,
        level: int = 1,
        content: Sequence[MarkdownElement | str] = [],
        subsections: Sequence[MarkdownSection] = []):
        """
        Construct a Markdown section with heading level, title string, and an optional 
        `Sequence` (used instead of `list` for type checking...) for the initial content
        of strings or `MarkdownElements`, and an optional list of subsections.
        The level >= 1, although numbers bigger than 6 or so don't make much sense.
        The title must be non-empty, since it is needed to render the section header.
        Don't pass `MarkdownSections` as `content`; use the `subsections` instead.
        """
        super().__init__(title)
        assert title, "MarkdownSection titles can't be empty!"
        assert level > 0, f"Invalid level '{level}' (must be > 0)"
        self.level = level
        # we store the content in a map by keys and rely on the python Dict 
        # implementation feature that insertion order is preserved.
        self.content: list[MarkdownElement] = []
        self.subsections: dict[str,MarkdownSection] = {}
        self.add_intro_content(content)
        self.add_subsections(subsections)

    def set_intro_content(self, content: Sequence[MarkdownElement | str]):
        """
        Replace the lines (or elements like tables, ...) for the content at the top
        of the section. Note that subsections added using `add_subsections` 
        will be rendered _below_ the content at the top.
        Don't pass `MarkdownSections` as `content`; use the `subsections` instead.
        """
        self.content = []
        self.add_intro_content(content)

    def add_intro_content(self, content: Sequence[MarkdownElement | str]):
        """
        Add lines (or elements like tables, ...) to the content at the top
        of the section. Note that subsections added using `add_subsections` 
        will be rendered _below_ the content at the top.
        Don't pass `MarkdownSections` as `content`; use the `subsections` instead.
        """
        for item in content:
            if isinstance(item, MarkdownSection):
                raise ValueError(f"Don't pass MarkdownSections as intro content. Use add/set_subsections instead! item = {item}")
            elif isinstance(item, MarkdownElement):
                self.content.append(item)
            else:
                self.content.append(MarkdownElement(title=str(item)))

    def set_subsections(self, subsections: Sequence[MarkdownSection]):
        """
        Replace the subsections.
        NOTE: All the levels will be reset to to the parent's level + 1, unless they
        are already >= level+1!
        """
        self.subsections = {}
        self.add_subsections(subsections)
        
    def set_subsections_as_dict(self, subsections: Mapping[str,MarkdownSection]):
        """
        Replace the subsections.
        NOTE: All the levels will be reset to to the parent's level + 1, unless they
        are already >= level+1!
        """
        self.subsections = {}
        self.add_subsections_as_dict(subsections)
        
    def add_subsections(self, subsections: Sequence[MarkdownSection]):
        """
        Add subsections. They will be stored in a dictionary ordered by insertion order
        (a Python dict implementation feature...), which we need to support rendering in
        the correct order. So, insert the subsections in the correct order for displaying.
        The element titles will be used as the keys. Hence, use non-empty titles for any 
        subsections provided. Storing in a dict allows subsequent updating of a subsection
        by referring to it by its key. However, this method raises a `ValueError` if any
        keys in the new subsections already exist in the current subsections.
        NOTE: All the levels will be reset as needed to be >= the parent's level + 1.
        """
        ss = dict([(s.title, s) for s in subsections])
        self.add_subsections_as_dict(ss)

    def add_subsections_as_dict(self, subsections: Mapping[str,MarkdownSection]):
        """
        Add subsections, specified as a dictionary. They will be stored in a dictionary
        ordered by insertion order (a Python dict implementation feature...), which we 
        need to support rendering in the correct order. So, insert the subsections in the
        correct order for displaying. Storing in a dict allows subsequent updating of a 
        subsection by referring to it by its key. However, this method raises a `ValueError` 
        if any keys in the new subsections already exist in the current subsections.
        NOTE: All the levels will be reset as needed to be >= the parent's level + 1.
        """
        bad_elements = []
        bad_keys = []
        for key, ss in subsections.items():
            if key in self.subsections:
                bad_keys.append(key) 
            if not isinstance(ss, MarkdownSection):
                bad_elements.append(str(ss))
        error = 'add_subsections(): '
        if len(bad_keys) > 0:
            error += f"All new subsections must have a unique key. bad keys = {bad_keys}. Existing keys = <{self.subsections.keys()}>, new keys = <{subsections.keys()}>"
        if len(bad_elements) > 0:
            error += f"Only MarkdownSections may be added as subsections. Bad elements = <{bad_elements}>."
        if len(bad_keys) > 0 or len(bad_elements) > 0:
            raise ValueError(error)

        self.subsections.update(subsections)
        self._fix_levels()

    def clear(self):
        """Remove the leading content and subsections."""
        self.content = []
        self.subsections = {}

    def _fix_levels(self):
        """
        Make sure all hierarchies of sections have correct levels, i.e.,
        if this object has level `l`, then its subsections, must be `>= l+1`,
        there subsections must have levels `>= l+2`, etc.
        """
        for s in self.subsections.values():
            if s.level <= self.level:
                s.level = self.level+1 # reset!
            s._fix_levels()

    def __setitem__(self, key: str, item: MarkdownSection):
        """
        Allow dictionary-like indexing of subsections.
        While you can replace a subsection this way, you can also just fetch
        the items with `my_section['foo']` and edit it directly.
        """
        self.subsections[key] = item

    def __getitem__(self, key: str) -> MarkdownSection:
        """
        Allow dictionary-like indexing of subsections.
        While you can replace a subsection this way, you can also just fetch
        the items with `my_section['foo']` and edit it directly.
        """
        return self.subsections[key]
 
    def __repr__(self) -> str:
        def ss(key: str, subsection: MarkdownSection) -> str:
            return f"""<a id="{to_id(key)}"></a>\n\n{subsection}\n"""

        content_str = '\n'.join([str(c) for c in self.content])
        subsections_str = '\n'.join([ss(k,s) for k,s in self.subsections.items()])
        return f"{self.level*'#'} {self.title}\n\n{content_str}\n{subsections_str}"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, MarkdownSection):
            return False
        return  self.level == other.level \
            and self.content == other.content \
            and self.subsections == other.subsections
        
class MarkdownTable(MarkdownElement):
    def __init__(self, title: str = '', columns: Sequence[str] = [], columns_with_justifications: Sequence[tuple[str,str]] = []):
        """Only one of `columns` and `columns_with_justifications` can be non-empty!"""
        super().__init__(title)
        if columns and columns_with_justifications:
            raise ValueError("Must only specify non-empty 'columns' or 'columns_with_justifications'.")
        self.columns: list[str] = []
        self.columns_justifications: list[str] = []
        self.rows = []
        if columns:
            self.add_columns(columns)
        else:
            self.add_columns_with_justifications(columns_with_justifications)

    def add_columns(self, columns: Sequence[str]):
        """
        Append one or more columns to the list of columns, using left justification for all of them.
        """
        self.add_columns_with_justifications([(c, 'left') for c in columns])

    def add_columns_with_justifications(self, columns: Sequence[tuple[str,str]]):
        """
        Append one or more columns to the list of columns. In the tuples,
        the first elements are the column names and the second elements are
        the justification strings, where the allowed justification values are:
        * `left`   means left justification 
        * `center` means center justification 
        * `right`  means right justification 
        Left justification is the default, so `` is interpreted as left justification.
        """
        if len(columns) == 0:
            return 
        self.columns.extend([c[0] for c in columns])
        self.columns_justifications.extend([MarkdownTable.justify(c[0], c[1]) for c in columns])

    def add_row(self, row: Sequence[Any]):
        """
        Add a row of values to the table. The length of `row` must match the number of columns.
        """
        if len(row) != len(self.columns):
            raise ValueError(f"Wrong number of cells in row: {len(row)}. Expected {len(self.columns)}.")
        self.rows.append(row)

    def add_row_with_dict(self, row: Mapping[str,Any]):
        """
        Add a row of values to the table, where the "cells" are specified in a dictionary 
        where the keys must be in the set of column names and empty values will be used
        for the unspecified cells.
        """
        # Check that no unknown columns are specified.
        names = set(self.columns)
        keys = set(row.keys())
        if names.union(keys) != names:
            raise ValueError(f"At least one unexpected column name <{keys}> that isn't in the set of columns = <{names}>")
        new_row = [row.get(name, '') for name in self.columns]
        self.rows.append(new_row)

    justifications = {'left', 'center', 'full', 'right', ''}

    def is_justification(value: str) -> bool:
        return value in MarkdownTable.justifications

    def justify(column_name: str, justification: str) -> str:
        if not MarkdownTable.is_justification(justification):
            raise ValueError(f"Unrecognized column 'justify' value: <{justification}> (column_name = <{column_name}>)")
        else:
            num_dashes = len(column_name) - 2 if len(column_name) > 2 else 1
            dashes = '-'*(num_dashes)
            match justification:
                case 'right':
                    return f'-{dashes}:'
                case 'center' | 'full':
                    return f':{dashes}:'
                case _:  # 'left' | '' (other possibilities filtered by is_justifications())
                    return f':{dashes}-'

    def __repr__(self) -> str:
        title_str = '\n\n'
        if len(self.title) > 0:
            title_str = f"\n**Table: {self.title}**\n\n"

        if len(self.columns) == 0:
            return ''
        else:
            columns_str = self.__make_row(self.columns)
            columns_justifications_str = self.__make_row(self.columns_justifications)
            rows_strs = [ self.__make_row(row) for row in self.rows ]
            return f"{title_str}{columns_str}\n{columns_justifications_str}\n{'\n'.join(rows_strs)}\n"

    def __which_type(self, values: Sequence[str] | Sequence[tuple[str,Any]] | Mapping[str,Any]) -> Optional[str]:
        """Return a string with the type for `values`. If empty, then `Sequence[str]` is returned."""
        def type_error():
            tcol  = f"type(values) = <{type(values)}>"
            raise ValueError(f"Unexpected argument type: {tcol}, values = <{values}>")

        if len(values) == 0:
            return 'Sequence[str]'
        elif type(values) is Sequence:
            t0 = type(values[0])
            if t0 is str:
                return 'Sequence[str]'
            elif t0 is tuple:
                return 'Sequence[tuple]'
            else:
                type_error()
        elif type(values) is Mapping:
            return 'Mapping'
        else:
            type_error()

    def __make_row(self, values: Sequence[Any]) -> str:
        if len(values) == 0:
            return '' 
        else:
            return f"| {' | '.join([str(v) for v in values])} |"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, MarkdownTable):
            return False
        return  self.columns == other.columns \
            and self.columns_justifications == other.columns_justifications \
            and self.rows == other.rows
        

class MarkdownTree(MarkdownElement):
    """Whereas MarkdownTable wrapped str, here we need hierarchical data."""

    default_bullet = '*'
    default_indentation = '  '

    def __init__(self, 
        label: str | int | float, 
        bullet: Optional[str] = None, 
        indentation: Optional[str] = None):
        super().__init__(str(label))
        self.children: list[MarkdownTree] = []
        self.label = label
        self.bullet = bullet
        if bullet:
            MarkdownTree.enforce_valid_bullet(bullet)
        self.indentation = indentation

    def add(self, child: MarkdownElement | str) -> MarkdownElement:
        """
        Add a sub bullet and return it.
        Python doesn't allow the `child` or return type to be declared
        `MarkdownTree`, because it is being defined! However, we convert
        `child` to a tree if it is not one already, and we return the tree,
        even though the declaration suggests a `MarkdownElement` can be
        returned.
        """
        def to_tree(child: MarkdownElement | str) -> MarkdownTree:
            if type(child) is MarkdownTree:
                return child
            elif type(child) is MarkdownElement:
                return MarkdownTree(label=child.title)
            else:
                return MarkdownTree(label=str(child))
            
        c = to_tree(child)
        self.children.append(c)
        return c

    def add_children(self, children: Sequence[MarkdownElement | str]) -> Sequence[MarkdownElement]:
        """
        Add multiple sub bullets and return them.
        Python doesn't allow the `children` or return type to be declared
        `Sequence[MarkdownTree]`, because `MarkdownTree` is being defined! However,
        we convert the `children` to trees, if they are not trees already, and 
        we return the list of trees, even though the declaration suggests a
        `Sequence[MarkdownElement]` can be returned.
        """
        return [self.add(child) for child in children]

    def __tri(self, first: Optional[str], second: Optional[str], third: str, 
        check: Callable[[str],str] = lambda s: str(s)) -> str:
        if first:
            return check(first)
        elif second:
            return check(second)
        else:
            return check(third)

    def as_strs(self, level: int, parent_bullet: str, parent_indent: str) -> Sequence[str]:
        bullet = self.get_bullet(default=parent_bullet)
        indent = self.get_indentation(default=parent_indent)
        indent_str = level*indent
        lines = [f"{indent_str}{bullet} {self.label}"]
        for child in self.children:
            lines.extend(child.as_strs(level+1, parent_bullet, parent_indent))
        return lines
        #return [f"{indent_str}{line}" for line in lines]

    def __repr__(self) -> str:
        return "\n".join(self.as_strs(0, self.get_bullet(), self.get_indentation()))

    number_re = re.compile(r'^\d+$')
    letter_re = re.compile(r'^\W$')

    def get_bullet(self, default: Optional[str] = None) -> str:
        """
        Return the defined bullet, or return `default`, if defined,
        or else return `MarkdownTree.default_bullet`.
        """
        return self.__tri(self.bullet, default, MarkdownTree.default_bullet,
            MarkdownTree.enforce_valid_bullet)

    def get_indentation(self, default: Optional[str] = None) -> str:
        """
        Return the defined indentation, or return `default`, if defined,
        or else return `MarkdownTree.default_indentation`.
        """
        return self.__tri(self.indentation, default, MarkdownTree.default_indentation)

    def enforce_valid_bullet(bullet: Optional[str]) -> str:
        if MarkdownTree.validate_bullet(bullet):
            return str(bullet)  # Wrap in str() to make ty typechecker happy.
        else:
            raise ValueError(f"Disallowed bullet value {bullet}. Must be '*', '-', a number, or a letter.")

    def validate_bullet(bullet: Optional[str]) -> bool:
        if not bullet:
            return False
        elif bullet == '*' or bullet == '-' \
            or MarkdownTree.number_re.match(bullet) or MarkdownTree.letter_re.match(bullet):
            return True 
        else:
            return False

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, MarkdownTree):
            return False
        return  self.label == other.label \
            and self.get_bullet() == other.get_bullet() \
            and self.get_indentation() == other.get_indentation() \
            and self.children == other.children 
