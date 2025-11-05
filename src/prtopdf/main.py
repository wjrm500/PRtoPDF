"""
GitHub PR to PDF Converter
Converts a GitHub pull request to an anonymised PDF document.
Usage: uv run prtopdf <PR_URL>
"""

import sys

from prtopdf.generator import create_pdf
from prtopdf.github_api import GitHubAPI


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

        # Initialize GitHub API client
        api = GitHubAPI()

        # Fetch data
        print("Fetching PR details...")
        pr_data = api.get_pull_request(owner, repo, pr_number)

        print("Fetching commits...")
        commits_data = api.get_pull_request_commits(owner, repo, pr_number)

        print("Fetching file changes...")
        files_data = api.get_pull_request_files(owner, repo, pr_number)

        # Generate PDF
        output_filename = f"PR-{pr_number}-evidence.pdf"
        create_pdf(pr_data, commits_data, files_data, output_filename, api)

    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
