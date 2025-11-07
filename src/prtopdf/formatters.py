"""Text formatting utilities for PDF generation."""

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
