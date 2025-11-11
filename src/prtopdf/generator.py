"""PDF generation using Playwright (headless Chrome)."""

import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.sync_api import sync_playwright

from prtopdf.config import DEFAULT_REDACTIONS, AnonymisationConfig
from prtopdf.formatters import format_datetime, format_file_info, format_markdown
from prtopdf.github_api import CommitData, FileData, GitHubAPI, PRData


def strip_markdown_links(text: str) -> str:
    """Remove markdown hyperlinks but keep the link text.

    Example: [Google](https://google.com) -> Google
    """
    return re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)


def prepare_template_data(
    pr_data: PRData,
    commits_data: list[CommitData],
    files_data: list[FileData],
    api: GitHubAPI,
    config: AnonymisationConfig | None = None,
) -> dict:
    """Prepare all data for template rendering."""
    redact = config["redactions"] if config else DEFAULT_REDACTIONS

    owner = pr_data["base"]["repo"]["owner"]["login"]
    repo = pr_data["base"]["repo"]["name"]

    # Determine state
    if pr_data.get("draft"):
        state = "Draft"
    elif pr_data.get("merged_at"):
        state = "Merged"
    else:
        state = pr_data["state"].capitalize()

    # Prepare metadata
    metadata = {}

    if not redact.get("metadata_author"):
        metadata["author"] = pr_data["user"]["login"]

    if not redact.get("metadata_created_at"):
        metadata["created_at"] = format_datetime(pr_data["created_at"])

    if not redact.get("metadata_branches"):
        metadata["head_branch"] = pr_data["head"]["ref"]
        metadata["base_branch"] = pr_data["base"]["ref"]

    metadata["state"] = state

    # Add merge/close information
    if pr_data.get("merged_at"):
        if not redact.get("metadata_closed_merged_by") and pr_data.get("merged_by"):
            metadata["merged_by"] = pr_data["merged_by"]["login"]
        if not redact.get("metadata_closed_merged_at"):
            metadata["merged_at"] = format_datetime(pr_data["merged_at"])
    elif pr_data["state"] == "closed" and pr_data.get("closed_at"):
        if not redact.get("metadata_closed_merged_by") and pr_data.get("closed_by"):
            metadata["closed_by"] = pr_data["closed_by"]["login"]
        if not redact.get("metadata_closed_merged_at"):
            metadata["closed_at"] = format_datetime(pr_data["closed_at"])

    # Prepare PR description
    description = pr_data.get("body", "")
    if redact.get("pr_description_links"):
        description = strip_markdown_links(description)
    description_html = format_markdown(description)

    # Prepare commits
    commits = []
    for commit in commits_data:
        commit_msg = commit["commit"]["message"]
        lines = commit_msg.split("\n", 1)
        commit_title = lines[0]
        commit_body = lines[1].strip() if len(lines) > 1 else ""

        commit_sha = commit["sha"]
        short_sha = commit_sha[:7]

        # Get author and committer
        author_obj = commit.get("author") or {}
        author_username = author_obj.get("login") or commit["commit"]["author"].get(
            "name", "unknown"
        )

        committer_obj = commit.get("committer") or {}
        committer_username = committer_obj.get("login") or commit["commit"][
            "committer"
        ].get("name")

        # Check if committer is different from author
        author_id = author_obj.get("id")
        committer_id = committer_obj.get("id")
        show_committer = (
            committer_username
            and author_id != committer_id
            and author_username != committer_username
        )

        commit_date = format_datetime(commit["commit"]["author"]["date"])

        # Get files for this commit
        commit_details = api.get_commit(owner, repo, commit_sha)
        files = [format_file_info(file) for file in commit_details.get("files", [])]

        commit_data = {
            "title": commit_title,
            "body": commit_body,
            "files": files,
        }

        # Add optional fields based on redaction config
        if not redact.get("commit_author"):
            commit_data["author"] = author_username

        if not redact.get("commit_committer") and show_committer:
            commit_data["committer"] = committer_username

        if not redact.get("commit_date"):
            commit_data["date"] = commit_date

        if not redact.get("commit_sha"):
            commit_data["sha"] = short_sha

        commits.append(commit_data)

    # Prepare file summary
    files_summary = [format_file_info(file) for file in files_data]
    total_additions = sum(f.get("additions", 0) for f in files_data)
    total_deletions = sum(f.get("deletions", 0) for f in files_data)

    template_data = {
        "title": pr_data["title"],
        "description_html": description_html,
        "metadata": metadata,
        "commits": commits,
        "files_summary": files_summary,
        "total_files": len(files_data),
        "total_additions": total_additions,
        "total_deletions": total_deletions,
    }

    # Add optional fields based on redaction config
    if not redact.get("repo_info"):
        template_data["owner"] = owner
        template_data["repo"] = repo

    if not redact.get("pr_number"):
        template_data["pr_number"] = pr_data["number"]

    return template_data


def create_pdf(
    pr_data: PRData,
    commits_data: list[CommitData],
    files_data: list[FileData],
    output_filename: str,
    api: GitHubAPI,
    config: AnonymisationConfig | None = None,
) -> None:
    """Generate PDF document from PR data using Jinja2 template and Playwright."""
    # Set up Jinja2 environment
    templates_dir = Path(__file__).parent / "templates"
    env = Environment(
        loader=FileSystemLoader(templates_dir),
        autoescape=select_autoescape(["html", "xml"]),
    )

    # Prepare data
    data = prepare_template_data(pr_data, commits_data, files_data, api, config)

    # Render template
    template = env.get_template("pr_report.html")
    html_content = template.render(**data)

    # Generate PDF using Playwright
    print(f"Generating PDF: {output_filename}")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html_content)
        page.pdf(path=output_filename, format="A4", print_background=True)
        browser.close()
    print("PDF generated successfully!")
