"""
GitHub PR to PDF Converter
Converts a GitHub pull request to an anonymised PDF document.
Usage: uv run prtopdf <PR_URL>
"""

import argparse
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
    parser = argparse.ArgumentParser(
        description="Convert GitHub pull requests to professional PDF documents",
        epilog="""
Examples:
  uv run prtopdf https://github.com/owner/repo/pull/123
  uv run prtopdf https://github.com/owner/repo/pull/123 --anonymise
  uv run prtopdf https://github.com/owner/repo/pull/123 --anonymise-default
  uv run prtopdf https://github.com/owner/repo/pull/123 --no-cache
  uv run prtopdf https://github.com/owner/repo/pull/123 --diffs-by-commit
  uv run prtopdf https://github.com/owner/repo/pull/123 --diffs-overall
  uv run prtopdf https://github.com/owner/repo/pull/123 --diffs-by-commit --diffs-overall

For private repositories, set GITHUB_TOKEN environment variable:
  export GITHUB_TOKEN=ghp_your_token_here
  Or create a .env file with: GITHUB_TOKEN=ghp_your_token_here
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("pr_url", help="GitHub pull request URL")

    anonymise_group = parser.add_mutually_exclusive_group()
    anonymise_group.add_argument(
        "--anonymise",
        action="store_true",
        help="Interactive config selection/creation",
    )
    anonymise_group.add_argument(
        "--anonymise-default",
        action="store_true",
        help="Use default.json config (quick)",
    )

    parser.add_argument(
        "--diffs-by-commit",
        action="store_true",
        help="Show code diffs for each commit",
    )
    parser.add_argument(
        "--diffs-overall",
        action="store_true",
        help="Show code diffs in overall summary",
    )

    parser.add_argument(
        "--no-cache", action="store_true", help="Disable API response caching"
    )

    args = parser.parse_args()

    # Determine config
    config = None
    if args.anonymise:
        config_filename = select_config_interactive()
        config = load_config(config_filename)
        print(f"\nUsing config: {config_filename}")
    elif args.anonymise_default:
        config = load_config("default.json")
        print("Using default anonymisation config")

    # Determine diff options
    show_commit_diffs = args.diffs_by_commit
    show_overall_diffs = args.diffs_overall

    if show_commit_diffs and show_overall_diffs:
        print("Including diffs for each commit and in overall summary")
    elif show_commit_diffs:
        print("Including diffs for each commit")
    elif show_overall_diffs:
        print("Including diffs in overall summary")

    try:
        # Parse URL
        owner, repo, pr_number = parse_pr_url(args.pr_url)
        print(f"Processing PR #{pr_number} from {owner}/{repo}")

        # Get token from environment
        load_dotenv()
        token = os.environ.get("GITHUB_TOKEN")

        # Initialise GitHub API client with token
        use_cache = not args.no_cache
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
        create_pdf(
            pr_data,
            commits_data,
            files_data,
            output_filename,
            api,
            config,
            show_commit_diffs,
            show_overall_diffs,
        )

    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
