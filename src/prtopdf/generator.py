"""PDF generation orchestration."""

from typing import Any

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate

from prtopdf.github_api import CommitData, FileData, GitHubAPI, PRData
from prtopdf.sections import (
    create_commits_section,
    create_description_section,
    create_metadata_section,
    create_summary_section,
    create_title_section,
)
from prtopdf.styles import create_styles


def create_pdf(
    pr_data: PRData,
    commits_data: list[CommitData],
    files_data: list[FileData],
    output_filename: str,
    api: GitHubAPI,
    anonymise: bool = False,
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

    styles = create_styles()
    story: list[Any] = []

    # Build document by composing section flowables
    story.extend(create_title_section(pr_data, styles))
    story.extend(create_metadata_section(pr_data, styles, anonymise))
    story.extend(create_description_section(pr_data, styles))
    story.extend(create_commits_section(pr_data, commits_data, api, styles))
    story.extend(create_summary_section(files_data, styles))

    print(f"Generating PDF: {output_filename}")
    doc.build(story)
    print("PDF generated successfully!")
