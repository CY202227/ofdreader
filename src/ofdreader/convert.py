"""Helpers to export OFD content to PDF."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import BinaryIO

from ofdreader._package import resolve_path
from ofdreader._xml import (
    find_child,
    find_children,
    get_attr,
    iter_descendants,
    parse_root,
)
from ofdreader.reader import OfdReader
from ofdreader.reader import _parse_box, _text_object_plain_text

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas
except ImportError:  # pragma: no cover - optional dependency
    A4 = None
    canvas = None
    pdfmetrics = None
    UnicodeCIDFont = None
    TTFont = None

_MM_TO_PT = 72.0 / 25.4


def _wrap_line(text: str, font_name: str, font_size: float, max_width: float) -> list[str]:
    """Wrap a single logical line to fit page width."""
    if not text:
        return [""]
    chunks: list[str] = []
    current = ""
    for char in text:
        candidate = current + char
        width = pdfmetrics.stringWidth(candidate, font_name, font_size)
        if width <= max_width:
            current = candidate
        else:
            if current:
                chunks.append(current)
            current = char
    if current:
        chunks.append(current)
    return chunks or [""]


def ofd_to_pdf(
    source: str | Path | bytes | BinaryIO | OfdReader,
    output_pdf: str | Path,
    *,
    font_name: str = "STSong-Light",
    font_size: float = 11.0,
    margin: float = 48.0,
    line_height: float = 16.0,
) -> Path:
    """Export OFD text to a simple paragraph-preserving PDF file.

    This exporter uses `OfdReader.extract_text()` output, so paragraphs are
    preserved (line wraps joined inside each paragraph).
    """
    if canvas is None or pdfmetrics is None or UnicodeCIDFont is None:
        raise ImportError(
            "reportlab is required for PDF export. Install with: pip install reportlab"
        )

    reader = source if isinstance(source, OfdReader) else OfdReader(source)
    output_path = Path(output_pdf)

    pdfmetrics.registerFont(UnicodeCIDFont(font_name))
    pdf = canvas.Canvas(str(output_path), pagesize=A4)
    _apply_pdf_metadata(pdf, reader, output_path)
    width, height = A4
    y = height - margin
    text_max_width = width - (2 * margin)

    for page in reader.pages:
        page_text = page.extract_text(
            preserve_layout=True,
            skip_whitespace=True,
        )
        paragraphs = page_text.split("\n")
        for paragraph in paragraphs:
            wrapped = _wrap_line(paragraph, font_name, font_size, text_max_width)
            for line in wrapped:
                if y < margin:
                    pdf.showPage()
                    pdf.setFont(font_name, font_size)
                    y = height - margin
                pdf.setFont(font_name, font_size)
                pdf.drawString(margin, y, line)
                y -= line_height
        # page separator
        y -= line_height
        if y < margin:
            pdf.showPage()
            y = height - margin

    pdf.save()
    return output_path


def _mm_to_pt(value: float) -> float:
    return value * _MM_TO_PT


def _pdf_meta_title(reader: OfdReader, output_path: Path) -> str:
    title = reader.metadata.get("Title", "").strip()
    if title:
        return title
    return output_path.stem


def _apply_pdf_metadata(pdf, reader: OfdReader, output_path: Path) -> None:
    pdf.setTitle(_pdf_meta_title(reader, output_path))
    author = reader.metadata.get("Author", "").strip()
    if author:
        pdf.setAuthor(author)
    creator = reader.metadata.get("Creator", "").strip()
    if creator:
        pdf.setCreator(creator)


def _load_public_fonts(reader: OfdReader) -> dict[str, str]:
    """Load OFD embedded fonts into reportlab and return ID->pdf font name."""
    font_map: dict[str, str] = {}
    public_res = reader.document.public_res
    if not public_res:
        return font_map

    try:
        res_root = parse_root(reader.package.read_bytes(public_res))
    except Exception:
        return font_map

    fonts_node = find_child(res_root, "Fonts")
    if fonts_node is None:
        return font_map

    package = reader.package
    doc_dir = reader.document.doc_dir
    temp_dir = Path(tempfile.mkdtemp(prefix="ofdreader_fonts_"))

    for font_elem in find_children(fonts_node, "Font"):
        font_id = get_attr(font_elem, "ID")
        if not font_id:
            continue
        font_file_elem = find_child(font_elem, "FontFile")
        if font_file_elem is None or not font_file_elem.text:
            continue
        base_loc = get_attr(res_root, "BaseLoc") or ""
        rel_file = font_file_elem.text.strip()
        res_path = resolve_path(resolve_path(doc_dir, base_loc), rel_file)
        try:
            font_bytes = package.read_bytes(res_path)
        except Exception:
            continue
        safe_name = f"ofd_font_{font_id}"
        ext = Path(rel_file).suffix or ".ttf"
        font_path = temp_dir / f"{safe_name}{ext}"
        font_path.write_bytes(font_bytes)
        try:
            if TTFont is None:
                continue
            pdfmetrics.registerFont(TTFont(safe_name, str(font_path)))
            font_map[font_id] = safe_name
        except Exception:
            continue
    return font_map


def ofd_to_pdf_layout(
    source: str | Path | bytes | BinaryIO | OfdReader,
    output_pdf: str | Path,
    *,
    fallback_font: str = "STSong-Light",
    default_font_size: float = 10.5,
) -> Path:
    """Export OFD with approximate original layout and embedded fonts.

    - Keeps page size from OFD `PageArea.PhysicalBox`
    - Draws each `TextObject` using `Boundary` absolute coordinates
    - Prefers embedded `PublicRes` fonts when available
    """
    if canvas is None or pdfmetrics is None or UnicodeCIDFont is None:
        raise ImportError(
            "reportlab is required for PDF export. Install with: pip install reportlab"
        )

    reader = source if isinstance(source, OfdReader) else OfdReader(source)
    output_path = Path(output_pdf)
    pdfmetrics.registerFont(UnicodeCIDFont(fallback_font))
    font_map = _load_public_fonts(reader)

    page_box = reader.document.page_area or (0.0, 0.0, 210.0, 297.0)
    page_width_pt = _mm_to_pt(page_box[2])
    page_height_pt = _mm_to_pt(page_box[3])

    pdf = canvas.Canvas(str(output_path), pagesize=(page_width_pt, page_height_pt))
    _apply_pdf_metadata(pdf, reader, output_path)

    for page in reader.pages:
        root = page._load_content()  # noqa: SLF001
        page_area = find_child(root, "Area")
        if page_area is not None:
            box_elem = find_child(page_area, "PhysicalBox")
            if box_elem is not None and box_elem.text:
                box = _parse_box(box_elem.text.strip())
                if box is not None:
                    page_width_pt = _mm_to_pt(box[2])
                    page_height_pt = _mm_to_pt(box[3])
                    pdf.setPageSize((page_width_pt, page_height_pt))

        for text_obj in iter_descendants(root, "TextObject"):
            text = _text_object_plain_text(text_obj, skip_whitespace=True)
            if not text:
                continue
            boundary = _parse_box(get_attr(text_obj, "Boundary"))
            if boundary is None:
                continue
            x_mm, y_mm, _w_mm, h_mm = boundary
            font_id = get_attr(text_obj, "Font")
            font_name = font_map.get(font_id or "", fallback_font)
            size_raw = get_attr(text_obj, "Size")
            try:
                font_size = float(size_raw) if size_raw else default_font_size
            except ValueError:
                font_size = default_font_size

            x_pt = _mm_to_pt(x_mm)
            baseline_pt = page_height_pt - _mm_to_pt(y_mm + h_mm) + 1.0
            pdf.setFont(font_name, font_size)
            pdf.drawString(x_pt, baseline_pt, text)

        pdf.showPage()

    pdf.save()
    return output_path

