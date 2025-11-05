"""PDF style definitions."""

from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet


def create_styles() -> dict[str, ParagraphStyle]:
    """Create and return custom paragraph styles for PDF generation."""
    base_styles = getSampleStyleSheet()

    return {
        "title": ParagraphStyle(
            "CustomTitle",
            parent=base_styles["Normal"],
            fontSize=18,
            fontName="Helvetica-Bold",
            alignment=TA_CENTER,
            spaceAfter=6,
            leading=24,
            textColor="#000000",
        ),
        "repo": ParagraphStyle(
            "CustomRepo",
            parent=base_styles["Normal"],
            fontSize=11,
            fontName="Helvetica",
            alignment=TA_CENTER,
            spaceAfter=4,
            textColor="#333333",
        ),
        "heading": ParagraphStyle(
            "CustomHeading",
            parent=base_styles["Normal"],
            fontSize=13,
            fontName="Helvetica-Bold",
            spaceAfter=10,
            spaceBefore=16,
            textColor="#000000",
        ),
        "subheading": ParagraphStyle(
            "CustomSubheading",
            parent=base_styles["Normal"],
            fontSize=11,
            fontName="Helvetica-Bold",
            spaceAfter=6,
            spaceBefore=10,
            textColor="#000000",
        ),
        "body": ParagraphStyle(
            "CustomBody",
            parent=base_styles["Normal"],
            fontSize=10,
            fontName="Helvetica",
            alignment=TA_LEFT,
            spaceAfter=6,
            leading=14,
            textColor="#000000",
        ),
        "code": ParagraphStyle(
            "CustomCode",
            parent=base_styles["Normal"],
            fontSize=9,
            fontName="Courier",
            leftIndent=20,
            spaceAfter=4,
            leading=12,
            textColor="#000000",
        ),
    }
