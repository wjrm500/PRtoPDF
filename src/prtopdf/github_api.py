"""
Lightweight GitHub API client.
"""

import json
import sys
import urllib.error
import urllib.request
from typing import Any, TypedDict


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


class GitHubAPI:
    """Simple client for GitHub API v3."""

    BASE_URL = "https://api.github.com"

    def __init__(self, token: str | None = None):
        """
        Initialise GitHub API client.

        Args:
            token: Optional GitHub personal access token for authenticated requests.
        """
        self.token = token

    def _request(self, endpoint: str) -> Any:
        """
        Make a GET request to the GitHub API.

        Args:
            endpoint: API endpoint (e.g., '/repos/owner/repo/pulls/123')

        Returns:
            JSON response as a Python object.

        Raises:
            SystemExit: On HTTP or URL errors.
        """
        url = f"{self.BASE_URL}{endpoint}"
        request = urllib.request.Request(url)

        if self.token:
            request.add_header("Authorization", f"token {self.token}")

        request.add_header("Accept", "application/vnd.github.v3+json")

        try:
            with urllib.request.urlopen(request) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as e:
            print(f"HTTP Error {e.code}: {e.reason}")
            if e.code == 401:
                print("Authentication failed. Check your token.")
            elif e.code == 404:
                print("Resource not found. Check the URL.")
            sys.exit(1)
        except urllib.error.URLError as e:
            print(f"URL Error: {e.reason}")
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
