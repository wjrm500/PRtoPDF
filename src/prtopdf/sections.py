"""PDF section builders - pure functions that return flowables."""

from datetime import datetime
from typing import Any

from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, Spacer

from prtopdf.formatters import format_file_info, format_multiline
from prtopdf.github_api import CommitData, FileData, GitHubAPI, PRData


def create_title_section(
    pr_data: PRData, styles: dict[str, ParagraphStyle]
) -> list[Any]:
    """Create title section flowables."""
    owner = pr_data["base"]["repo"]["owner"]["login"]
    repo = pr_data["base"]["repo"]["name"]
    pr_number = pr_data["number"]

    return [
        Paragraph(f"{owner}/{repo}", styles["repo"]),
        Spacer(1, 0.1 * inch),
        Paragraph(f"Pull Request #{pr_number}: {pr_data['title']}", styles["title"]),
        Spacer(1, 0.1 * inch),
    ]


def create_metadata_section(
    pr_data: PRData, styles: dict[str, ParagraphStyle], anonymise: bool = False
) -> list[Any]:
    """Create metadata section flowables."""
    metadata = ""

    if not anonymise:
        author = pr_data["user"]["login"]
        metadata += f"<b>Author:</b> {author}<br/>"

    created_at = datetime.strptime(pr_data["created_at"], "%Y-%m-%dT%H:%M:%SZ")
    metadata += f"<b>Created:</b> {created_at.strftime('%Y-%m-%d')}<br/>"

    state = "Merged" if pr_data.get("merged_at") else pr_data["state"].capitalize()
    metadata += f"<b>State:</b> {state}<br/>"

    if pr_data.get("merged_at"):
        merged_at = datetime.strptime(pr_data["merged_at"], "%Y-%m-%dT%H:%M:%SZ")
        metadata += f"<b>Merged:</b> {merged_at.strftime('%Y-%m-%d')}<br/>"

    return [
        Paragraph(metadata, styles["body"]),
        Spacer(1, 0.1 * inch),
    ]


def create_description_section(
    pr_data: PRData, styles: dict[str, ParagraphStyle]
) -> list[Any]:
    """Create description section flowables."""
    description = pr_data.get("body", "").strip()
    if not description:
        description = "No description provided."

    formatted_description = format_multiline(description)

    return [
        Paragraph("1. Pull Request Description", styles["heading"]),
        Paragraph(formatted_description, styles["body"]),
        Spacer(1, 0.1 * inch),
    ]


def create_commits_section(
    pr_data: PRData,
    commits_data: list[CommitData],
    api: GitHubAPI,
    styles: dict[str, ParagraphStyle],
) -> list[Any]:
    """Create commits section flowables."""
    flowables: list[Any] = [Paragraph("2. Commits", styles["heading"])]

    owner = pr_data["base"]["repo"]["owner"]["login"]
    repo = pr_data["base"]["repo"]["name"]

    for commit in commits_data:
        flowables.extend(_create_commit_flowables(commit, owner, repo, api, styles))

    flowables.append(Spacer(1, 0.1 * inch))
    return flowables


def _create_commit_flowables(
    commit: CommitData,
    owner: str,
    repo: str,
    api: GitHubAPI,
    styles: dict[str, ParagraphStyle],
) -> list[Any]:
    """Create flowables for a single commit."""
    flowables: list[Any] = []

    # Parse commit message
    commit_msg = commit["commit"]["message"]
    lines = commit_msg.split("\n", 1)
    commit_title = lines[0]
    commit_body = lines[1].strip() if len(lines) > 1 else ""

    # Add commit title
    flowables.append(Paragraph(f"<b>Commit:</b> {commit_title}", styles["subheading"]))

    # Add commit body if present
    if commit_body:
        formatted_body = format_multiline(commit_body)
        flowables.append(Paragraph(formatted_body, styles["body"]))

    # Add files changed
    flowables.append(Paragraph("<b>Files changed in this commit:</b>", styles["body"]))

    commit_sha = commit["sha"]
    commit_details = api.get_commit(owner, repo, commit_sha)

    for file in commit_details.get("files", []):
        flowables.append(Paragraph(format_file_info(file), styles["code"]))

    return flowables


def create_summary_section(
    files_data: list[FileData], styles: dict[str, ParagraphStyle]
) -> list[Any]:
    """Create summary section flowables."""
    flowables: list[Any] = [
        Paragraph("3. Overall Summary of Changes", styles["heading"])
    ]

    # Calculate totals
    total_additions = sum(f.get("additions", 0) for f in files_data)
    total_deletions = sum(f.get("deletions", 0) for f in files_data)
    total_files = len(files_data)

    summary = f"<b>Total files changed:</b> {total_files}<br/>"
    summary += f"<b>Total lines added:</b> +{total_additions}<br/>"
    summary += f"<b>Total lines removed:</b> -{total_deletions}<br/>"

    flowables.extend(
        [
            Paragraph(summary, styles["body"]),
            Spacer(1, 0.1 * inch),
            Paragraph("<b>Files changed:</b>", styles["body"]),
        ]
    )

    # Add file list
    for file in files_data:
        flowables.append(Paragraph(format_file_info(file), styles["code"]))

    return flowables
