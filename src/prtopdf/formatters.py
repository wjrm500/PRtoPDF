"""Text formatting utilities for PDF generation."""

from typing import Any

from prtopdf.github_api import FileData


def escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def format_multiline(text: str) -> str:
    """Format multiline text for PDF, escaping HTML and preserving line breaks."""
    return escape_html(text).replace("\n", "<br/>")


def get_change_status(status: str) -> str:
    """Convert GitHub file status to readable format."""
    status_map = {
        "added": "New",
        "modified": "Amended",
        "removed": "Removed",
        "renamed": "Renamed",
    }
    return status_map.get(status, status.capitalize())


def format_file_info(file: FileData | dict[str, Any]) -> str:
    """Format file change information for display."""
    filename = file["filename"]
    status = get_change_status(file["status"])
    additions = file.get("additions", 0)
    deletions = file.get("deletions", 0)
    return f"• {filename} ({status}, +{additions}/-{deletions})"
