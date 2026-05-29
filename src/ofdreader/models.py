"""Data models for parsed OFD structures."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class OutlineItem:
    """Document outline (bookmark) entry."""

    title: str
    page_id: int | None = None
    dest_type: str | None = None
    left: float | None = None
    top: float | None = None


@dataclass
class PageRef:
    """Reference to a page content file within the document."""

    page_id: int
    base_loc: str
    index: int
    physical_box: tuple[float, float, float, float] | None = None


@dataclass
class DocumentInfo:
    """Parsed document body metadata."""

    doc_root: str
    doc_dir: str
    public_res: str | None = None
    max_unit_id: int = 0
    page_area: tuple[float, float, float, float] | None = None
    pages: list[PageRef] = field(default_factory=list)
    outlines: list[OutlineItem] = field(default_factory=list)
    custom_tags: str | None = None
