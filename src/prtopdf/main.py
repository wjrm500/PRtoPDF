"""
GitHub PR to PDF Converter
Converts a GitHub pull request to an anonymised PDF document.
Usage: uv run prtopdf <PR_URL>
"""

import json
import sys
import urllib.error
import urllib.request
from datetime import datetime
from typing import Any, TypedDict

from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


class PRData(TypedDict, total=False):
    title: str
    created_at: str
    state: str
    merged_at: str
    body: str
    base: dict[str, Any]


class CommitData(TypedDict):
    sha: str
    commit: dict[str, Any]


class FileData(TypedDict, total=False):
    filename: str
    status: str
    additions: int
    deletions: int


def parse_pr_url(url: str) -> tuple[str, str, str]:
    """Extract owner, repo, and PR number from GitHub URL."""
    parts = url.rstrip("/").split("/")

    if "github.com" not in url or "pull" not in parts:
        raise ValueError("Invalid GitHub PR URL")

    try:
        pull_index = parts.index("pull")
        pr_number = parts[pull_index + 1]
        repo = parts[pull_index - 1]
        owner = parts[pull_index - 2]
        return owner, repo, pr_number
    except (IndexError, ValueError):
        raise ValueError("Could not parse PR URL")


def fetch_json(url: str) -> Any:
    """Fetch JSON data from a URL."""
    try:
        with urllib.request.urlopen(url) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}")
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"URL Error: {e.reason}")
        sys.exit(1)


def fetch_pr_data(
    owner: str, repo: str, pr_number: str
) -> tuple[PRData, list[CommitData], list[FileData]]:
    """Fetch PR details, commits, and files from GitHub API."""
    base_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"

    print("Fetching PR details...")
    pr_data = fetch_json(base_url)

    print("Fetching commits...")
    commits_data = fetch_json(f"{base_url}/commits")

    print("Fetching file changes...")
    files_data = fetch_json(f"{base_url}/files")

    return pr_data, commits_data, files_data


def get_change_status(status: str) -> str:
    """Convert GitHub file status to readable format."""
    status_map = {
        "added": "New",
        "modified": "Amended",
        "removed": "Removed",
        "renamed": "Renamed",
    }
    return status_map.get(status, status.capitalize())


def create_pdf(
    pr_data: PRData,
    commits_data: list[CommitData],
    files_data: list[FileData],
    output_filename: str,
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

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=16,
        alignment=TA_CENTER,
        spaceAfter=20,
    )

    heading_style = ParagraphStyle(
        "CustomHeading",
        parent=styles["Heading2"],
        fontSize=14,
        spaceAfter=12,
        spaceBefore=12,
    )

    subheading_style = ParagraphStyle(
        "CustomSubheading",
        parent=styles["Heading3"],
        fontSize=12,
        spaceAfter=8,
        spaceBefore=8,
    )

    body_style = ParagraphStyle(
        "CustomBody",
        parent=styles["Normal"],
        fontSize=10,
        alignment=TA_LEFT,
        spaceAfter=6,
    )

    code_style = ParagraphStyle(
        "CustomCode", parent=styles["Code"], fontSize=9, leftIndent=20, spaceAfter=4
    )

    story = []

    # Title
    title = Paragraph(f"Pull Request: {pr_data['title']}", title_style)
    story.append(title)
    story.append(Spacer(1, 0.2 * inch))

    # PR metadata (anonymised)
    created_at = datetime.strptime(pr_data["created_at"], "%Y-%m-%dT%H:%M:%SZ")
    metadata = f"<b>Created:</b> {created_at.strftime('%Y-%m-%d')}<br/>"
    metadata += f"<b>State:</b> {pr_data['state'].capitalize()}<br/>"
    if pr_data.get("merged_at"):
        merged_at = datetime.strptime(pr_data["merged_at"], "%Y-%m-%dT%H:%M:%SZ")
        metadata += f"<b>Merged:</b> {merged_at.strftime('%Y-%m-%d')}<br/>"
    story.append(Paragraph(metadata, body_style))
    story.append(Spacer(1, 0.3 * inch))

    # Section 1: PR Description
    story.append(Paragraph("1. Pull Request Description", heading_style))
    description = pr_data.get("body", "No description provided.")
    if not description or description.strip() == "":
        description = "No description provided."
    # Escape HTML and preserve line breaks
    description = (
        description.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )
    description = description.replace("\n", "<br/>")
    story.append(Paragraph(description, body_style))
    story.append(Spacer(1, 0.3 * inch))

    # Section 2: Commits
    story.append(Paragraph("2. Commits", heading_style))

    for commit in commits_data:
        commit_msg = commit["commit"]["message"]
        lines = commit_msg.split("\n", 1)
        commit_title = lines[0]
        commit_body = lines[1].strip() if len(lines) > 1 else ""

        # Commit title
        story.append(Paragraph(f"<b>Commit:</b> {commit_title}", subheading_style))

        # Commit message body
        if commit_body:
            commit_body_escaped = (
                commit_body.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )
            commit_body_escaped = commit_body_escaped.replace("\n", "<br/>")
            story.append(Paragraph(commit_body_escaped, body_style))

        # Files changed in this commit
        story.append(Paragraph("<b>Files changed in this commit:</b>", body_style))

        # Get files for this commit
        commit_sha = commit["sha"]
        commit_files_url = f"https://api.github.com/repos/{pr_data['base']['repo']['owner']['login']}/{pr_data['base']['repo']['name']}/commits/{commit_sha}"  # noqa: E501
        commit_details = fetch_json(commit_files_url)

        for file in commit_details.get("files", []):
            filename = file["filename"]
            status = get_change_status(file["status"])
            additions = file.get("additions", 0)
            deletions = file.get("deletions", 0)

            file_info = f"• {filename} ({status}, +{additions}/-{deletions})"
            story.append(Paragraph(file_info, code_style))

        story.append(Spacer(1, 0.15 * inch))

    story.append(Spacer(1, 0.2 * inch))

    # Section 3: Overall Summary
    story.append(Paragraph("3. Overall Summary of Changes", heading_style))

    # Calculate totals
    total_additions = sum(f.get("additions", 0) for f in files_data)
    total_deletions = sum(f.get("deletions", 0) for f in files_data)
    total_files = len(files_data)

    summary = f"<b>Total files changed:</b> {total_files}<br/>"
    summary += f"<b>Total lines added:</b> +{total_additions}<br/>"
    summary += f"<b>Total lines removed:</b> -{total_deletions}<br/>"
    story.append(Paragraph(summary, body_style))
    story.append(Spacer(1, 0.2 * inch))

    # List all files
    story.append(Paragraph("<b>Files changed:</b>", body_style))
    for file in files_data:
        filename = file["filename"]
        status = get_change_status(file["status"])
        additions = file.get("additions", 0)
        deletions = file.get("deletions", 0)

        file_info = f"• {filename} ({status}, +{additions}/-{deletions})"
        story.append(Paragraph(file_info, code_style))

    # Build PDF
    print(f"Generating PDF: {output_filename}")
    doc.build(story)
    print("PDF generated successfully!")


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: uv run prtopdf <PR_URL>")
        print("Example: uv run prtopdf https://github.com/owner/repo/pull/123")
        sys.exit(1)

    pr_url = sys.argv[1]

    try:
        # Parse URL
        owner, repo, pr_number = parse_pr_url(pr_url)
        print(f"Processing PR #{pr_number} from {owner}/{repo}")

        # Fetch data
        pr_data, commits_data, files_data = fetch_pr_data(owner, repo, pr_number)

        # Generate PDF
        output_filename = f"PR-{pr_number}-evidence.pdf"
        create_pdf(pr_data, commits_data, files_data, output_filename)

    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
