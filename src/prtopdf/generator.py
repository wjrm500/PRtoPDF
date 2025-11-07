"""PDF generation using Playwright (headless Chrome)."""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.sync_api import sync_playwright

from prtopdf.formatters import format_datetime, format_file_info, format_markdown
from prtopdf.github_api import CommitData, FileData, GitHubAPI, PRData


def prepare_template_data(
    pr_data: PRData,
    commits_data: list[CommitData],
    files_data: list[FileData],
    api: GitHubAPI,
    anonymise: bool = False,
) -> dict:
    """Prepare all data for template rendering."""
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
    metadata = {
        "author": pr_data["user"]["login"] if not anonymise else None,
        "created_at": format_datetime(pr_data["created_at"]),
        "head_branch": pr_data["head"]["ref"],
        "base_branch": pr_data["base"]["ref"],
        "state": state,
    }

    # Add merge/close information
    if pr_data.get("merged_at"):
        metadata["merged_by"] = (
            pr_data["merged_by"]["login"]
            if not anonymise and pr_data.get("merged_by")
            else None
        )
        metadata["merged_at"] = format_datetime(pr_data["merged_at"])
    elif pr_data["state"] == "closed" and pr_data.get("closed_at"):
        metadata["closed_by"] = (
            pr_data["closed_by"]["login"]
            if not anonymise and pr_data.get("closed_by")
            else None
        )
        metadata["closed_at"] = format_datetime(pr_data["closed_at"])

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

        commits.append(
            {
                "title": commit_title,
                "body": commit_body,
                "sha": short_sha,
                "author": author_username if not anonymise else None,
                "committer": (
                    committer_username if (not anonymise and show_committer) else None
                ),
                "date": commit_date,
                "files": files,
            }
        )

    # Prepare file summary
    files_summary = [format_file_info(file) for file in files_data]
    total_additions = sum(f.get("additions", 0) for f in files_data)
    total_deletions = sum(f.get("deletions", 0) for f in files_data)

    return {
        "owner": owner,
        "repo": repo,
        "pr_number": pr_data["number"],
        "title": pr_data["title"],
        "description_html": format_markdown(pr_data.get("body", "")),
        "metadata": metadata,
        "commits": commits,
        "files_summary": files_summary,
        "total_files": len(files_data),
        "total_additions": total_additions,
        "total_deletions": total_deletions,
        "anonymise": anonymise,
    }


def create_pdf(
    pr_data: PRData,
    commits_data: list[CommitData],
    files_data: list[FileData],
    output_filename: str,
    api: GitHubAPI,
    anonymise: bool = False,
) -> None:
    """Generate PDF document from PR data using Jinja2 template and Playwright."""
    # Set up Jinja2 environment
    templates_dir = Path(__file__).parent / "templates"
    env = Environment(
        loader=FileSystemLoader(templates_dir),
        autoescape=select_autoescape(["html", "xml"]),
    )

    # Prepare data
    data = prepare_template_data(pr_data, commits_data, files_data, api, anonymise)

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
