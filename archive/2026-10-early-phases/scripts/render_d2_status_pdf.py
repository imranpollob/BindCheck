#!/usr/bin/env python3
"""Render the D2 evidence-status manuscript as a reviewable PDF.

This renderer intentionally targets the concise Markdown status manuscript,
not the historical submission draft. It uses only local input and writes one
stable PDF under output/pdf/ for the Step 20 PDF-only review passes.
"""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path
from typing import Iterable

from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "paper/d2-status-draft.md"
DEFAULT_OUTPUT = ROOT / "output/pdf/bindcheck-d2-evidence-status.pdf"


def ascii_safe(text: str) -> str:
    """Normalize typography that is unreliable in the built-in PDF fonts."""

    replacements = {
        "\u2010": "-",
        "\u2011": "-",
        "\u2012": "-",
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
        "\u2192": "->",
        "\u2190": "<-",
        "\u21d2": "=>",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2026": "...",
        "\u00a0": " ",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return text


def inline_markup(text: str) -> str:
    """Convert a small, deterministic Markdown inline subset to ReportLab XML."""

    text = ascii_safe(text.strip())
    links: list[tuple[str, str]] = []

    def hold_link(match: re.Match[str]) -> str:
        token = f"@@LINK{len(links)}@@"
        links.append((match.group(1), match.group(2)))
        return token

    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", hold_link, text)
    text = html.escape(text, quote=True)
    text = re.sub(r"`([^`]+)`", r'<font name="Courier">\1</font>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", text)
    for index, (label, target) in enumerate(links):
        safe_label = html.escape(ascii_safe(label), quote=True)
        safe_target = html.escape(target, quote=True)
        replacement = f'<link href="{safe_target}" color="#205493">{safe_label}</link>'
        text = text.replace(f"@@LINK{index}@@", replacement)
    return text


def is_table_separator(line: str) -> bool:
    cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells)


def parse_table(lines: list[str], start: int) -> tuple[list[list[str]], int]:
    rows: list[list[str]] = []
    index = start
    while index < len(lines) and lines[index].lstrip().startswith("|"):
        row = [cell.strip() for cell in lines[index].strip().strip("|").split("|")]
        if not is_table_separator(lines[index]):
            rows.append(row)
        index += 1
    return rows, index


def styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    common = {
        "fontName": "Helvetica",
        "textColor": colors.HexColor("#172B3A"),
        "splitLongWords": True,
        "allowWidows": 0,
        "allowOrphans": 0,
    }
    return {
        "title": ParagraphStyle(
            "D2Title",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=21,
            leading=25,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#123B5D"),
            spaceAfter=16,
            keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "D2H2",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=17,
            textColor=colors.HexColor("#123B5D"),
            spaceBefore=12,
            spaceAfter=7,
            keepWithNext=True,
        ),
        "h3": ParagraphStyle(
            "D2H3",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11.5,
            leading=14,
            textColor=colors.HexColor("#28536B"),
            spaceBefore=9,
            spaceAfter=5,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "D2Body",
            parent=base["BodyText"],
            fontName=common["fontName"],
            fontSize=9.2,
            leading=12.2,
            textColor=common["textColor"],
            alignment=TA_LEFT,
            spaceAfter=6,
            splitLongWords=True,
            allowWidows=0,
            allowOrphans=0,
        ),
        "abstract": ParagraphStyle(
            "D2Abstract",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.1,
            leading=12,
            leftIndent=0.24 * inch,
            rightIndent=0.24 * inch,
            borderColor=colors.HexColor("#B9CBD8"),
            borderWidth=0.7,
            borderPadding=8,
            backColor=colors.HexColor("#F3F7FA"),
            spaceAfter=9,
            splitLongWords=True,
        ),
        "status": ParagraphStyle(
            "D2Status",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=10.5,
            leading=14,
            textColor=colors.HexColor("#7A281E"),
            borderColor=colors.HexColor("#D6A69F"),
            borderWidth=0.9,
            borderPadding=9,
            backColor=colors.HexColor("#FFF4F1"),
            spaceAfter=14,
            splitLongWords=True,
        ),
        "bullet": ParagraphStyle(
            "D2Bullet",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.1,
            leading=12,
            leftIndent=16,
            firstLineIndent=-8,
            bulletIndent=6,
            textColor=common["textColor"],
            spaceAfter=3,
            splitLongWords=True,
        ),
        "code": ParagraphStyle(
            "D2Code",
            parent=base["Code"],
            fontName="Courier",
            fontSize=7.4,
            leading=9.5,
            leftIndent=8,
            rightIndent=8,
            borderColor=colors.HexColor("#CED8DF"),
            borderWidth=0.5,
            borderPadding=6,
            backColor=colors.HexColor("#F6F8F9"),
            spaceAfter=7,
            splitLongWords=True,
        ),
        "table_header": ParagraphStyle(
            "D2TableHeader",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=7.3,
            leading=9,
            textColor=colors.white,
            splitLongWords=True,
        ),
        "table_cell": ParagraphStyle(
            "D2TableCell",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=7.1,
            leading=9,
            textColor=common["textColor"],
            splitLongWords=True,
        ),
    }


def table_flowable(rows: list[list[str]], available_width: float, style_map: dict[str, ParagraphStyle]) -> Table:
    columns = max(len(row) for row in rows)
    normalized = [row + [""] * (columns - len(row)) for row in rows]
    # Give narrative columns more room while keeping numeric columns compact.
    numeric = []
    for column in range(columns):
        values = [row[column].strip() for row in normalized[1:]]
        numeric.append(bool(values) and all(re.fullmatch(r"[0-9./%+-]+", value) for value in values if value))
    compact_total = sum(0.55 * inch for flag in numeric if flag)
    narrative_count = max(1, columns - sum(numeric))
    narrative_width = max(0.8 * inch, (available_width - compact_total) / narrative_count)
    widths = [0.55 * inch if flag else narrative_width for flag in numeric]
    scale = available_width / sum(widths)
    widths = [width * scale for width in widths]

    rendered: list[list[Paragraph]] = []
    for row_index, row in enumerate(normalized):
        cell_style = style_map["table_header"] if row_index == 0 else style_map["table_cell"]
        rendered.append([Paragraph(inline_markup(cell), cell_style) for cell in row])
    table = Table(rendered, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#28536B")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#AABAC5")),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F7F9")]),
            ]
        )
    )
    return table


def markdown_to_story(markdown: str, available_width: float) -> list[object]:
    style_map = styles()
    lines = markdown.splitlines()
    story: list[object] = []
    paragraph_lines: list[str] = []
    in_code = False
    code_lines: list[str] = []
    abstract_mode = False

    def flush_paragraph() -> None:
        nonlocal paragraph_lines
        if paragraph_lines:
            text = " ".join(line.strip() for line in paragraph_lines)
            story.append(Paragraph(inline_markup(text), style_map["abstract"] if abstract_mode else style_map["body"]))
            paragraph_lines = []

    index = 0
    while index < len(lines):
        line = lines[index].rstrip()
        stripped = line.strip()
        if stripped.startswith("```"):
            flush_paragraph()
            if in_code:
                code = "\n".join(ascii_safe(item) for item in code_lines)
                story.append(Paragraph(html.escape(code).replace("\n", "<br/>"), style_map["code"]))
                code_lines = []
                in_code = False
            else:
                in_code = True
            index += 1
            continue
        if in_code:
            code_lines.append(line)
            index += 1
            continue
        if not stripped:
            flush_paragraph()
            index += 1
            continue
        if stripped.startswith("|") and index + 1 < len(lines) and is_table_separator(lines[index + 1]):
            flush_paragraph()
            rows, index = parse_table(lines, index)
            story.extend([table_flowable(rows, available_width, style_map), Spacer(1, 8)])
            continue
        heading = re.match(r"^(#{1,3})\s+(.+)$", stripped)
        if heading:
            flush_paragraph()
            level = len(heading.group(1))
            title = heading.group(2)
            if title.lower() == "internal evidence map" and story:
                story.append(PageBreak())
            if level == 1:
                story.append(Paragraph(inline_markup(title), style_map["title"]))
            elif level == 2:
                abstract_mode = title.lower() == "abstract"
                story.append(Paragraph(inline_markup(title), style_map["h2"]))
            else:
                story.append(Paragraph(inline_markup(title), style_map["h3"]))
            index += 1
            continue
        if stripped.startswith(">"):
            flush_paragraph()
            quote_lines: list[str] = []
            while index < len(lines) and lines[index].lstrip().startswith(">"):
                quote_lines.append(lines[index].lstrip()[1:].strip())
                index += 1
            story.append(Paragraph(inline_markup(" ".join(quote_lines)), style_map["status"]))
            continue
        bullet = re.match(r"^[-*]\s+(.+)$", stripped)
        numbered = re.match(r"^(\d+)\.\s+(.+)$", stripped)
        if bullet or numbered:
            flush_paragraph()
            if bullet:
                marker, text = "-", bullet.group(1)
            else:
                marker, text = f"{numbered.group(1)}.", numbered.group(2)
            story.append(Paragraph(inline_markup(text), style_map["bullet"], bulletText=marker))
            index += 1
            continue
        paragraph_lines.append(line)
        index += 1
    flush_paragraph()
    if in_code and code_lines:
        code = "\n".join(ascii_safe(item) for item in code_lines)
        story.append(Paragraph(html.escape(code).replace("\n", "<br/>"), style_map["code"]))
    return story


def page_decor(canvas, document) -> None:  # type: ignore[no-untyped-def]
    canvas.saveState()
    width, height = letter
    canvas.setStrokeColor(colors.HexColor("#C4D1D9"))
    canvas.setLineWidth(0.5)
    canvas.line(document.leftMargin, height - 0.44 * inch, width - document.rightMargin, height - 0.44 * inch)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#536B7A"))
    canvas.drawString(document.leftMargin, height - 0.34 * inch, "BindCheck D2 - Evidence-Led Status")
    canvas.drawRightString(width - document.rightMargin, 0.34 * inch, f"Page {document.page}")
    canvas.restoreState()


def render(source: Path, destination: Path) -> dict[str, object]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    markdown = source.read_text(encoding="utf-8")
    document = SimpleDocTemplate(
        str(destination),
        pagesize=letter,
        leftMargin=0.68 * inch,
        rightMargin=0.68 * inch,
        topMargin=0.62 * inch,
        bottomMargin=0.58 * inch,
        title="BindCheck D2: Evidence-Led Status of Proof-to-Execution Binding Analysis",
        author="Anonymous research status draft",
        subject="Bounded D2 evidence status; not submission-ready",
    )
    story = markdown_to_story(markdown, letter[0] - document.leftMargin - document.rightMargin)
    document.build(story, onFirstPage=page_decor, onLaterPages=page_decor)

    reader = PdfReader(str(destination))
    extracted = "\n".join(page.extract_text() or "" for page in reader.pages)
    required = [
        "Research verdict UNKNOWN",
        "Gate A",
        "Not submission-ready",
        "producer_guarantee",
        "Gate B",
        "Gate C",
    ]
    missing = [token for token in required if token.lower() not in extracted.lower()]
    if missing:
        raise ValueError(f"rendered PDF is missing required text: {missing}")
    return {
        "source": str(source),
        "destination": str(destination),
        "pages": len(reader.pages),
        "characters_extracted": len(extracted),
        "required_text_missing": missing,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    result = render(arguments.input.resolve(), arguments.output.resolve())
    for key, value in result.items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
