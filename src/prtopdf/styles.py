"""PDF style definitions."""

from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet


def create_styles() -> dict[str, ParagraphStyle]:
    """Create and return custom paragraph styles for PDF generation."""
    base_styles = getSampleStyleSheet()

    return {
        "title": ParagraphStyle(
            "CustomTitle",
            parent=base_styles["Heading1"],
            fontSize=16,
            alignment=TA_CENTER,
            spaceAfter=20,
        ),
        "heading": ParagraphStyle(
            "CustomHeading",
            parent=base_styles["Heading2"],
            fontSize=14,
            spaceAfter=12,
            spaceBefore=12,
        ),
        "subheading": ParagraphStyle(
            "CustomSubheading",
            parent=base_styles["Heading3"],
            fontSize=12,
            spaceAfter=8,
            spaceBefore=8,
        ),
        "body": ParagraphStyle(
            "CustomBody",
            parent=base_styles["Normal"],
            fontSize=10,
            alignment=TA_LEFT,
            spaceAfter=6,
        ),
        "code": ParagraphStyle(
            "CustomCode",
            parent=base_styles["Code"],
            fontSize=9,
            leftIndent=20,
            spaceAfter=4,
        ),
    }
