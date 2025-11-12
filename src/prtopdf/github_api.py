"""
Lightweight GitHub API client.
"""

import sys
from typing import Any, TypedDict

import requests
import requests_cache


class PRData(TypedDict, total=False):
    number: int
    title: str
    created_at: str
    state: str
    merged_at: str
    closed_at: str
    merged_by: dict[str, Any]
    closed_by: dict[str, Any]
    body: str
    head: dict[str, Any]
    base: dict[str, Any]
    user: dict[str, Any]
    draft: bool


class CommitData(TypedDict):
    sha: str
    commit: dict[str, Any]
    author: dict[str, Any]
    committer: dict[str, Any]


class FileData(TypedDict, total=False):
    filename: str
    status: str
    additions: int
    deletions: int
    patch: str


class GitHubAPI:
    """Simple client for GitHub API v3."""

    BASE_URL = "https://api.github.com"

    def __init__(self, token: str | None = None, use_cache: bool = True):
        """
        Initialise GitHub API client.

        Args:
            token: Optional GitHub personal access token for authenticated requests.
            use_cache: Whether to use file-based caching (default: True)
        """
        self.token = token

        if use_cache:
            self.session = requests_cache.CachedSession(
                ".cache/github_api", expire_after=3600
            )
        else:
            self.session = requests.Session()

        if token:
            self.session.headers.update({"Authorization": f"token {token}"})
        self.session.headers.update({"Accept": "application/vnd.github.v3+json"})

    def _request(self, endpoint: str) -> Any:
        """
        Make a GET request to the GitHub API.

        Args:
            endpoint: API endpoint (e.g., '/repos/owner/repo/pulls/123')

        Returns:
            JSON response as a Python object.

        Raises:
            SystemExit: On HTTP errors.
        """
        url = f"{self.BASE_URL}{endpoint}"

        try:
            response = self.session.get(url)

            # Log cache status
            if hasattr(response, "from_cache") and response.from_cache:
                print(f"[CACHE] {endpoint}")
            else:
                print(f"[API] {endpoint}")

            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            print(f"HTTP Error {e.response.status_code}: {e.response.reason}")
            if e.response.status_code == 401:
                print("Authentication failed. Check your token.")
            elif e.response.status_code == 404:
                print("Resource not found. Check the URL.")
            sys.exit(1)
        except requests.RequestException as e:
            print(f"Request Error: {e}")
            sys.exit(1)

    def get_pull_request(self, owner: str, repo: str, pr_number: str) -> PRData:
        """
        Get pull request details.

        Args:
            owner: Repository owner.
            repo: Repository name.
            pr_number: Pull request number.

        Returns:
            Pull request data.
        """
        endpoint = f"/repos/{owner}/{repo}/pulls/{pr_number}"
        return self._request(endpoint)

    def get_pull_request_commits(
        self, owner: str, repo: str, pr_number: str
    ) -> list[CommitData]:
        """
        Get commits for a pull request.

        Args:
            owner: Repository owner.
            repo: Repository name.
            pr_number: Pull request number.

        Returns:
            List of commit data.
        """
        endpoint = f"/repos/{owner}/{repo}/pulls/{pr_number}/commits"
        return self._request(endpoint)

    def get_pull_request_files(
        self, owner: str, repo: str, pr_number: str
    ) -> list[FileData]:
        """
        Get files changed in a pull request.

        Args:
            owner: Repository owner.
            repo: Repository name.
            pr_number: Pull request number.

        Returns:
            List of file data.
        """
        endpoint = f"/repos/{owner}/{repo}/pulls/{pr_number}/files"
        return self._request(endpoint)

    def get_commit(self, owner: str, repo: str, sha: str) -> dict[str, Any]:
        """
        Get commit details including files.

        Args:
            owner: Repository owner.
            repo: Repository name.
            sha: Commit SHA.

        Returns:
            Commit data including files.
        """
        endpoint = f"/repos/{owner}/{repo}/commits/{sha}"
        return self._request(endpoint)

    def get_issue(self, owner: str, repo: str, issue_number: str) -> dict[str, Any]:
        """
        Get issue details (includes closed_by for PRs).

        Args:
            owner: Repository owner.
            repo: Repository name.
            issue_number: Issue/PR number.

        Returns:
            Issue data.
        """
        endpoint = f"/repos/{owner}/{repo}/issues/{issue_number}"
        return self._request(endpoint)
