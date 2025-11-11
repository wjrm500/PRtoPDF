"""
GitHub PR to PDF Converter
Converts a GitHub pull request to an anonymised PDF document.
Usage: uv run prtopdf <PR_URL>
"""

import os
import sys

from dotenv import load_dotenv

from prtopdf.config import load_config, select_config_interactive
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
    if len(sys.argv) < 2:
        print(
            "Usage: uv run prtopdf <PR_URL> [--anonymise | --anonymise-default] [--no-cache]"
        )
        print("\nExamples:")
        print("  uv run prtopdf https://github.com/owner/repo/pull/123")
        print("  uv run prtopdf https://github.com/owner/repo/pull/123 --anonymise")
        print(
            "  uv run prtopdf https://github.com/owner/repo/pull/123 --anonymise-default"
        )
        print("  uv run prtopdf https://github.com/owner/repo/pull/123 --no-cache")
        print("\nFlags:")
        print("  --anonymise          Interactive config selection/creation")
        print("  --anonymise-default  Use default.json config (quick)")
        print("  --no-cache           Disable API response caching")
        print("\nFor private repositories, set GITHUB_TOKEN environment variable:")
        print("  export GITHUB_TOKEN=ghp_your_token_here")
        print("  Or create a .env file with: GITHUB_TOKEN=ghp_your_token_here")
        sys.exit(1)

    pr_url = sys.argv[1]
    use_anonymise = "--anonymise" in sys.argv
    use_anonymise_default = "--anonymise-default" in sys.argv
    use_cache = "--no-cache" not in sys.argv

    # Determine config
    config = None
    if use_anonymise and use_anonymise_default:
        print("Error: Cannot use both --anonymise and --anonymise-default")
        sys.exit(1)
    elif use_anonymise:
        config_filename = select_config_interactive()
        config = load_config(config_filename)
        print(f"\nUsing config: {config_filename}")
    elif use_anonymise_default:
        config = load_config("default.json")
        print("Using default anonymisation config")

    try:
        # Parse URL
        owner, repo, pr_number = parse_pr_url(pr_url)
        print(f"Processing PR #{pr_number} from {owner}/{repo}")

        # Get token from environment
        load_dotenv()
        token = os.environ.get("GITHUB_TOKEN")

        # Initialise GitHub API client with token
        api = GitHubAPI(token=token, use_cache=use_cache)

        # Fetch data
        print("Fetching PR details...")
        pr_data = api.get_pull_request(owner, repo, pr_number)

        if pr_data["state"] == "closed" and not pr_data.get("merged_at"):
            # Fetch issue data to get closed_by
            issue_data = api.get_issue(owner, repo, pr_number)
            # Merge closed_by into pr_data
            if issue_data.get("closed_by"):
                pr_data["closed_by"] = issue_data["closed_by"]

        print("Fetching commits...")
        commits_data = api.get_pull_request_commits(owner, repo, pr_number)

        print("Fetching file changes...")
        files_data = api.get_pull_request_files(owner, repo, pr_number)

        # Generate PDF
        output_filename = f"PR-{pr_number}-evidence.pdf"
        create_pdf(pr_data, commits_data, files_data, output_filename, api, config)

    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
