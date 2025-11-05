"""
PDF generation logic for GitHub pull requests.
"""

from datetime import datetime
from typing import Any

from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from prtopdf.github_api import CommitData, FileData, GitHubAPI, PRData


def get_change_status(status: str) -> str:
    """Convert GitHub file status to readable format."""
    status_map = {
        "added": "New",
        "modified": "Amended",
        "removed": "Removed",
        "renamed": "Renamed",
    }
    return status_map.get(status, status.capitalize())


def _escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _create_styles() -> dict[str, ParagraphStyle]:
    """Create and return custom paragraph styles."""
    styles = getSampleStyleSheet()

    return {
        "title": ParagraphStyle(
            "CustomTitle",
            parent=styles["Heading1"],
            fontSize=16,
            alignment=TA_CENTER,
            spaceAfter=20,
        ),
        "heading": ParagraphStyle(
            "CustomHeading",
            parent=styles["Heading2"],
            fontSize=14,
            spaceAfter=12,
            spaceBefore=12,
        ),
        "subheading": ParagraphStyle(
            "CustomSubheading",
            parent=styles["Heading3"],
            fontSize=12,
            spaceAfter=8,
            spaceBefore=8,
        ),
        "body": ParagraphStyle(
            "CustomBody",
            parent=styles["Normal"],
            fontSize=10,
            alignment=TA_LEFT,
            spaceAfter=6,
        ),
        "code": ParagraphStyle(
            "CustomCode",
            parent=styles["Code"],
            fontSize=9,
            leftIndent=20,
            spaceAfter=4,
        ),
    }


def _add_title(story: list, pr_data: PRData, styles: dict[str, ParagraphStyle]) -> None:
    """Add title section to the PDF."""
    title = Paragraph(f"Pull Request: {pr_data['title']}", styles["title"])
    story.append(title)
    story.append(Spacer(1, 0.2 * inch))


def _add_metadata(
    story: list, pr_data: PRData, styles: dict[str, ParagraphStyle]
) -> None:
    """Add PR metadata section to the PDF."""
    created_at = datetime.strptime(pr_data["created_at"], "%Y-%m-%dT%H:%M:%SZ")
    metadata = f"<b>Created:</b> {created_at.strftime('%Y-%m-%d')}<br/>"
    metadata += f"<b>State:</b> {pr_data['state'].capitalize()}<br/>"
    if pr_data.get("merged_at"):
        merged_at = datetime.strptime(pr_data["merged_at"], "%Y-%m-%dT%H:%M:%SZ")
        metadata += f"<b>Merged:</b> {merged_at.strftime('%Y-%m-%d')}<br/>"
    story.append(Paragraph(metadata, styles["body"]))
    story.append(Spacer(1, 0.3 * inch))


def _add_description(
    story: list, pr_data: PRData, styles: dict[str, ParagraphStyle]
) -> None:
    """Add PR description section to the PDF."""
    story.append(Paragraph("1. Pull Request Description", styles["heading"]))
    description = pr_data.get("body", "No description provided.")
    if not description or description.strip() == "":
        description = "No description provided."
    description = _escape_html(description).replace("\n", "<br/>")
    story.append(Paragraph(description, styles["body"]))
    story.append(Spacer(1, 0.3 * inch))


def _add_commits(
    story: list,
    pr_data: PRData,
    commits_data: list[CommitData],
    api: GitHubAPI,
    styles: dict[str, ParagraphStyle],
) -> None:
    """Add commits section to the PDF."""
    story.append(Paragraph("2. Commits", styles["heading"]))

    owner = pr_data["base"]["repo"]["owner"]["login"]
    repo = pr_data["base"]["repo"]["name"]

    for commit in commits_data:
        commit_msg = commit["commit"]["message"]
        lines = commit_msg.split("\n", 1)
        commit_title = lines[0]
        commit_body = lines[1].strip() if len(lines) > 1 else ""

        # Commit title
        story.append(Paragraph(f"<b>Commit:</b> {commit_title}", styles["subheading"]))

        # Commit message body
        if commit_body:
            commit_body_escaped = _escape_html(commit_body).replace("\n", "<br/>")
            story.append(Paragraph(commit_body_escaped, styles["body"]))

        # Files changed in this commit
        story.append(Paragraph("<b>Files changed in this commit:</b>", styles["body"]))

        commit_sha = commit["sha"]
        commit_details = api.get_commit(owner, repo, commit_sha)

        for file in commit_details.get("files", []):
            filename = file["filename"]
            status = get_change_status(file["status"])
            additions = file.get("additions", 0)
            deletions = file.get("deletions", 0)

            file_info = f"• {filename} ({status}, +{additions}/-{deletions})"
            story.append(Paragraph(file_info, styles["code"]))

        story.append(Spacer(1, 0.15 * inch))

    story.append(Spacer(1, 0.2 * inch))


def _add_summary(
    story: list, files_data: list[FileData], styles: dict[str, ParagraphStyle]
) -> None:
    """Add overall summary section to the PDF."""
    story.append(Paragraph("3. Overall Summary of Changes", styles["heading"]))

    # Calculate totals
    total_additions = sum(f.get("additions", 0) for f in files_data)
    total_deletions = sum(f.get("deletions", 0) for f in files_data)
    total_files = len(files_data)

    summary = f"<b>Total files changed:</b> {total_files}<br/>"
    summary += f"<b>Total lines added:</b> +{total_additions}<br/>"
    summary += f"<b>Total lines removed:</b> -{total_deletions}<br/>"
    story.append(Paragraph(summary, styles["body"]))
    story.append(Spacer(1, 0.2 * inch))

    # List all files
    story.append(Paragraph("<b>Files changed:</b>", styles["body"]))
    for file in files_data:
        filename = file["filename"]
        status = get_change_status(file["status"])
        additions = file.get("additions", 0)
        deletions = file.get("deletions", 0)

        file_info = f"• {filename} ({status}, +{additions}/-{deletions})"
        story.append(Paragraph(file_info, styles["code"]))


def create_pdf(
    pr_data: PRData,
    commits_data: list[CommitData],
    files_data: list[FileData],
    output_filename: str,
    api: GitHubAPI,
) -> None:
    """Generate PDF document from PR data."""
    doc = SimpleDocTemplate(
        output_filename,
        pagesize=A4,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    styles = _create_styles()
    story: list[Any] = []

    _add_title(story, pr_data, styles)
    _add_metadata(story, pr_data, styles)
    _add_description(story, pr_data, styles)
    _add_commits(story, pr_data, commits_data, api, styles)
    _add_summary(story, files_data, styles)

    print(f"Generating PDF: {output_filename}")
    doc.build(story)
    print("PDF generated successfully!")
