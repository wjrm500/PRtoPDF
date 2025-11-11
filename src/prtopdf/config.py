"""Configuration management for anonymisation."""

import json
import sys
from pathlib import Path
from typing import TypedDict

import inquirer
from inquirer import themes
from inquirer.themes import Theme


class RedactionConfig(TypedDict):
    repo_info: bool
    pr_number: bool
    metadata_author: bool
    metadata_created_at: bool
    metadata_branches: bool
    metadata_closed_merged_by: bool
    metadata_closed_merged_at: bool
    pr_description_links: bool
    commit_author: bool
    commit_committer: bool
    commit_date: bool
    commit_sha: bool


class AnonymisationConfig(TypedDict):
    description: str
    redactions: RedactionConfig


CONFIGS_DIR = Path(__file__).parent / "configs"

DEFAULT_REDACTIONS: RedactionConfig = {
    "repo_info": False,
    "pr_number": False,
    "metadata_author": False,
    "metadata_created_at": False,
    "metadata_branches": False,
    "metadata_closed_merged_by": False,
    "metadata_closed_merged_at": False,
    "pr_description_links": False,
    "commit_author": False,
    "commit_committer": False,
    "commit_date": False,
    "commit_sha": False,
}


# Custom theme with colors
class MinimalTheme(Theme):
    def __init__(self):
        super().__init__()
        # Question styling
        self.Question.mark_color = themes.term.cyan
        self.Question.brackets_color = themes.term.normal

        # List styling - cursor only
        self.List.selection_color = themes.term.cyan  # Selected item in cyan
        self.List.selection_cursor = "❯ "
        self.List.unselected_color = themes.term.bright_black  # Unselected in gray
        self.List.unselected_cursor = "  "


# ANSI color codes (for non-inquirer parts)
class Colors:
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    MAGENTA = "\033[95m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


def get_available_configs() -> list[tuple[str, str]]:
    """Get list of available config files with their descriptions.

    Returns:
        List of tuples: (filename, description)
    """
    configs = []
    for config_file in CONFIGS_DIR.glob("*.json"):
        try:
            with open(config_file) as f:
                data = json.load(f)
                description = data.get("description", "No description")
                configs.append((config_file.name, description))
        except Exception:
            continue
    return sorted(configs)


def load_config(filename: str) -> AnonymisationConfig:
    """Load a configuration file.

    Args:
        filename: Name of config file (e.g., 'default.json')

    Returns:
        Configuration dictionary
    """
    config_path = CONFIGS_DIR / filename
    if not config_path.exists():
        print(
            f"{Colors.YELLOW}Error: Config file not found: {config_path}{Colors.RESET}"
        )
        sys.exit(1)

    try:
        with open(config_path) as f:
            config = json.load(f)
            # Validate structure
            if "redactions" not in config:
                raise ValueError("Config missing 'redactions' key")
            return config
    except json.JSONDecodeError as e:
        print(f"{Colors.YELLOW}Error: Invalid JSON in config file: {e}{Colors.RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"{Colors.YELLOW}Error loading config: {e}{Colors.RESET}")
        sys.exit(1)


def create_config_interactive() -> str:
    """Interactive config creation via CLI prompts.

    Returns:
        Filename of created config
    """
    print(
        f"\n{Colors.CYAN}{Colors.BOLD}Create new anonymisation config{Colors.RESET}\n"
    )

    # Get filename
    while True:
        filename = input(
            f"{Colors.MAGENTA}Config filename{Colors.RESET} (e.g., 'my_config.json'): "
        ).strip()
        if not filename:
            print(f"{Colors.YELLOW}Filename cannot be empty{Colors.RESET}")
            continue
        if not filename.endswith(".json"):
            filename += ".json"

        config_path = CONFIGS_DIR / filename
        if config_path.exists():
            overwrite = (
                input(
                    f"{Colors.YELLOW}'{filename}' already exists. Overwrite?{Colors.RESET} (y/N): "
                )
                .strip()
                .lower()
            )
            if overwrite != "y":
                continue
        break

    # Get description
    description = input(f"{Colors.MAGENTA}Description{Colors.RESET}: ").strip()
    if not description:
        description = "Custom anonymisation config"

    print(f"\n{Colors.DIM}For each item, choose whether to redact it:")
    print("  y = redact/remove")
    print(f"  n = keep (default){Colors.RESET}\n")

    # Prompts for each redaction option
    prompts = [
        ("repo_info", "Repository name (owner/repo)"),
        ("pr_number", "Pull request number"),
        ("metadata_author", '"Created by" username'),
        ("metadata_created_at", '"Created at" timestamp'),
        ("metadata_branches", "Branch information (head → base)"),
        ("metadata_closed_merged_by", '"Merged by" / "Closed by" username'),
        ("metadata_closed_merged_at", '"Merged at" / "Closed at" timestamp'),
        ("pr_description_links", "Hyperlinks in PR description (keep text)"),
        ("commit_author", "Commit author usernames"),
        ("commit_committer", "Commit committer usernames"),
        ("commit_date", "Commit timestamps"),
        ("commit_sha", "Commit SHA hashes"),
    ]

    redactions: dict[str, bool] = {}
    for key, label in prompts:
        response = (
            input(
                f"{Colors.DIM}[{len(redactions)+1}/{len(prompts)}]{Colors.RESET} "
                f"Redact {Colors.MAGENTA}{label}{Colors.RESET}? (y/N): "
            )
            .strip()
            .lower()
        )
        redactions[key] = response == "y"

    # Create config
    config = {"description": description, "redactions": redactions}

    # Save to file
    config_path = CONFIGS_DIR / filename
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    print(f"\n{Colors.GREEN}✓ Config saved: {filename}{Colors.RESET}")
    return filename


def select_config_interactive() -> str:
    """Interactive config selection from available configs.

    Returns:
        Filename of selected config
    """
    configs = get_available_configs()

    print(f"\n{Colors.CYAN}{Colors.BOLD}Select anonymisation config{Colors.RESET}\n")

    # Calculate max filename length for alignment
    max_filename_length = max((len(filename) for filename, _ in configs), default=0)

    # Build choices as PLAIN TEXT (no ANSI codes)
    # inquirer will handle coloring via the theme
    choices = ["✨ Create new config"]
    choice_map: dict[int, str | None] = {0: None}  # 0 maps to create new

    for i, (filename, description) in enumerate(configs, 1):
        # Pad filename to align descriptions
        padded_filename = filename.ljust(max_filename_length)
        display = f"{padded_filename}  │  {description}"
        choices.append(display)
        choice_map[i] = filename

    # Create menu question
    questions = [
        inquirer.List(
            "config",
            message="Use arrow keys to navigate, Enter to select",
            choices=choices,
            carousel=True,
        ),
    ]

    try:
        answers = inquirer.prompt(questions, theme=MinimalTheme())
        if answers is None:
            print(f"\n{Colors.YELLOW}Cancelled{Colors.RESET}")
            sys.exit(0)

        selected = answers["config"]
        selected_index = choices.index(selected)

        if selected_index == 0:
            return create_config_interactive()
        else:
            selected_filename = choice_map[selected_index]
            if selected_filename is None:
                # This should never happen, but handle it
                print(f"\n{Colors.YELLOW}Error: Invalid selection{Colors.RESET}")
                sys.exit(1)
            return selected_filename
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Cancelled{Colors.RESET}")
        sys.exit(0)
