"""Text formatting utilities for PDF generation."""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import markdown
from markdown.extensions.codehilite import CodeHiliteExtension
from markdown.extensions.fenced_code import FencedCodeExtension
from markdown.extensions.nl2br import Nl2BrExtension
from markdown.extensions.tables import TableExtension

from prtopdf.github_api import FileData


def format_markdown(text: str) -> str:
    """Convert markdown to HTML with GitHub-flavored extensions."""
    if not text or not text.strip():
        return "<p>No description provided.</p>"

    html = markdown.markdown(
        text,
        extensions=[
            FencedCodeExtension(),
            TableExtension(),
            Nl2BrExtension(),
            CodeHiliteExtension(css_class="highlight", linenums=False),
            "sane_lists",
        ],
    )
    return html


def format_datetime(dt_str: str) -> str:
    """Format ISO datetime string to readable format."""
    dt = datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%SZ")
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")


def get_change_status(status: str) -> str:
    """Convert GitHub file status to readable format."""
    status_map = {
        "added": "New",
        "modified": "Amended",
        "removed": "Removed",
        "renamed": "Renamed",
    }
    return status_map.get(status, status.capitalize())


def format_file_info(file: FileData | dict[str, Any]) -> dict[str, Any]:
    """Format file change information for template."""
    return {
        "filename": file["filename"],
        "status": get_change_status(file["status"]),
        "additions": file.get("additions", 0),
        "deletions": file.get("deletions", 0),
    }


@dataclass
class DiffLine:
    """Represents a single line in a diff."""

    type: str  # 'context', 'addition', 'deletion'
    old_line_num: int | None
    new_line_num: int | None
    content: str


@dataclass
class DiffHunk:
    """Represents a hunk (section) of changes in a diff."""

    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: list[DiffLine]


@dataclass
class ParsedDiff:
    """Represents a parsed diff for a file."""

    filename: str
    hunks: list[DiffHunk]


def parse_diff(patch: str, filename: str) -> ParsedDiff:
    """Parse a unified diff patch into structured data.

    Args:
        patch: Unified diff patch string from GitHub API
        filename: Name of the file being diffed

    Returns:
        ParsedDiff object with structured hunk data
    """
    if not patch:
        return ParsedDiff(filename=filename, hunks=[])

    hunks = []
    lines = patch.split("\n")

    i = 0
    while i < len(lines):
        line = lines[i]

        # Look for hunk header: @@ -old_start,old_count +new_start,new_count @@
        if line.startswith("@@"):
            match = re.match(r"@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@", line)
            if match:
                old_start = int(match.group(1))
                old_count = int(match.group(2)) if match.group(2) else 1
                new_start = int(match.group(3))
                new_count = int(match.group(4)) if match.group(4) else 1

                hunk_lines = []
                old_line = old_start
                new_line = new_start
                i += 1

                # Process lines in this hunk
                while i < len(lines) and not lines[i].startswith("@@"):
                    content_line = lines[i]

                    if not content_line:
                        # Empty line counts as context
                        hunk_lines.append(DiffLine("context", old_line, new_line, ""))
                        old_line += 1
                        new_line += 1
                    elif content_line.startswith("+"):
                        # Addition
                        hunk_lines.append(
                            DiffLine("addition", None, new_line, content_line[1:])
                        )
                        new_line += 1
                    elif content_line.startswith("-"):
                        # Deletion
                        hunk_lines.append(
                            DiffLine("deletion", old_line, None, content_line[1:])
                        )
                        old_line += 1
                    elif content_line.startswith(" "):
                        # Context
                        hunk_lines.append(
                            DiffLine("context", old_line, new_line, content_line[1:])
                        )
                        old_line += 1
                        new_line += 1
                    elif content_line.startswith("\\"):
                        # "\ No newline at end of file" - skip
                        pass
                    else:
                        # Treat as context if it doesn't start with special char
                        hunk_lines.append(
                            DiffLine("context", old_line, new_line, content_line)
                        )
                        old_line += 1
                        new_line += 1

                    i += 1

                hunks.append(
                    DiffHunk(
                        old_start=old_start,
                        old_count=old_count,
                        new_start=new_start,
                        new_count=new_count,
                        lines=hunk_lines,
                    )
                )
                continue

        i += 1

    return ParsedDiff(filename=filename, hunks=hunks)


def format_diff_for_template(parsed_diff: ParsedDiff) -> dict[str, Any]:
    """Format parsed diff for Jinja2 template rendering.

    Args:
        parsed_diff: ParsedDiff object

    Returns:
        Dictionary suitable for template rendering
    """
    formatted_hunks = []

    for hunk in parsed_diff.hunks:
        formatted_lines = []

        for line in hunk.lines:
            formatted_lines.append(
                {
                    "type": line.type,
                    "old_line_num": line.old_line_num,
                    "new_line_num": line.new_line_num,
                    "content": line.content,
                }
            )

        formatted_hunks.append(
            {
                "old_start": hunk.old_start,
                "new_start": hunk.new_start,
                "lines": formatted_lines,
            }
        )

    return {"filename": parsed_diff.filename, "hunks": formatted_hunks}
