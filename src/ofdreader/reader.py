"""OfdReader: PyPDF2-style read API for OFD documents."""

from __future__ import annotations

import re
from pathlib import Path
from typing import BinaryIO

from ofdreader._constants import OFD_XML_ENTRY
from ofdreader._package import OfdPackage, doc_dir_for, normalize_zip_path, resolve_path
from ofdreader._xml import (
    find_child,
    find_children,
    get_attr,
    iter_descendants,
    local_name,
    parse_root,
    text_content,
)
from ofdreader.exceptions import OfdFormatError, OfdNotFoundError
from ofdreader.models import DocumentInfo, OutlineItem, PageRef

_WHITESPACE_ONLY = re.compile(r"^[\s\u3000]*$")

def _parse_box(value: str | None) -> tuple[float, float, float, float] | None:
    if not value:
        return None
    parts = value.split()
    if len(parts) != 4:
        return None
    try:
        return tuple(float(p) for p in parts)  # type: ignore[return-value]
    except ValueError:
        return None


def _parse_docinfo(ofd_root) -> dict[str, str]:
    metadata: dict[str, str] = {}
    doc_body = find_child(ofd_root, "DocBody")
    if doc_body is None:
        raise OfdFormatError("OFD.xml missing DocBody")
    doc_info = find_child(doc_body, "DocInfo")
    if doc_info is None:
        return metadata
    for child in doc_info:
        name = local_name(child.tag)
        if name == "CustomDatas":
            for custom in find_children(child, "CustomData"):
                key = get_attr(custom, "Name")
                if key:
                    metadata[f"CustomData:{key}"] = text_content(custom)
            continue
        metadata[name] = text_content(child)
    return metadata


def _parse_doc_root(ofd_root) -> str:
    doc_body = find_child(ofd_root, "DocBody")
    if doc_body is None:
        raise OfdFormatError("OFD.xml missing DocBody")
    doc_root_elem = find_child(doc_body, "DocRoot")
    if doc_root_elem is None:
        raise OfdNotFoundError("OFD.xml missing DocRoot")
    doc_root = text_content(doc_root_elem)
    if not doc_root:
        raise OfdNotFoundError("DocRoot is empty")
    return normalize_zip_path(doc_root)


def _parse_document(document_root, doc_root_path: str) -> DocumentInfo:
    doc_dir = doc_dir_for(doc_root_path)
    info = DocumentInfo(doc_root=doc_root_path, doc_dir=doc_dir)

    common = find_child(document_root, "CommonData")
    if common is not None:
        max_unit = find_child(common, "MaxUnitID")
        if max_unit is not None and text_content(max_unit).isdigit():
            info.max_unit_id = int(text_content(max_unit))
        page_area = find_child(common, "PageArea")
        if page_area is not None:
            box = find_child(page_area, "PhysicalBox")
            info.page_area = _parse_box(text_content(box))
        public_res = find_child(common, "PublicRes")
        if public_res is not None:
            loc = text_content(public_res)
            if loc:
                info.public_res = resolve_path(doc_dir, loc)

    pages_elem = find_child(document_root, "Pages")
    if pages_elem is not None:
        for index, page_elem in enumerate(find_children(pages_elem, "Page")):
            page_id_str = get_attr(page_elem, "ID")
            base_loc = get_attr(page_elem, "BaseLoc") or text_content(page_elem)
            if not page_id_str or not base_loc:
                continue
            page_id = int(page_id_str)
            resolved = resolve_path(doc_dir, base_loc)
            info.pages.append(
                PageRef(page_id=page_id, base_loc=resolved, index=index)
            )

    outlines_elem = find_child(document_root, "Outlines")
    if outlines_elem is not None:
        for outline in find_children(outlines_elem, "OutlineElem"):
            title = get_attr(outline, "Title", "")
            page_id = None
            dest_type = None
            left = top = None
            actions = find_child(outline, "Actions")
            if actions is not None:
                action = find_child(actions, "Action")
                if action is not None:
                    goto = find_child(action, "Goto")
                    if goto is not None:
                        dest = find_child(goto, "Dest")
                        if dest is not None:
                            dest_type = get_attr(dest, "Type")
                            page_id_str = get_attr(dest, "PageID")
                            if page_id_str and page_id_str.isdigit():
                                page_id = int(page_id_str)
                            left_str = get_attr(dest, "Left")
                            top_str = get_attr(dest, "Top")
                            if left_str:
                                left = float(left_str)
                            if top_str:
                                top = float(top_str)
            info.outlines.append(
                OutlineItem(
                    title=title,
                    page_id=page_id,
                    dest_type=dest_type,
                    left=left,
                    top=top,
                )
            )

    custom_tags = find_child(document_root, "CustomTags")
    if custom_tags is not None:
        info.custom_tags = text_content(custom_tags)
        if info.custom_tags:
            info.custom_tags = resolve_path(doc_dir, info.custom_tags)

    return info


def extract_text_from_content_xml(content_root, *, skip_whitespace: bool = True) -> str:
    """Extract plain text from a Page Content.xml root element."""
    chunks: list[str] = []
    for text_obj in iter_descendants(content_root, "TextObject"):
        for text_code in iter_descendants(text_obj, "TextCode"):
            text = text_content(text_code)
            if not text:
                continue
            if skip_whitespace and _WHITESPACE_ONLY.match(text):
                continue
            chunks.append(text)
    return "".join(chunks)


class OfdPage:
    """A single page in an OFD document."""

    def __init__(
        self,
        reader: OfdReader,
        page_ref: PageRef,
    ) -> None:
        self._reader = reader
        self._page_ref = page_ref
        self._content_root = None

    @property
    def page_id(self) -> int:
        return self._page_ref.page_id

    @property
    def index(self) -> int:
        return self._page_ref.index

    @property
    def base_loc(self) -> str:
        return self._page_ref.base_loc

    def _load_content(self):
        if self._content_root is None:
            data = self._reader._package.read_bytes(self._page_ref.base_loc)
            root = parse_root(data)
            area = find_child(root, "Area")
            if area is not None:
                box = find_child(area, "PhysicalBox")
                self._page_ref.physical_box = _parse_box(text_content(box))
            self._content_root = root
        return self._content_root

    def extract_text(self, *, skip_whitespace: bool = True) -> str:
        """Return concatenated text from all TextObject elements on this page."""
        root = self._load_content()
        return extract_text_from_content_xml(root, skip_whitespace=skip_whitespace)


class OfdReader:
    """Read an OFD package (GB/T 33190) from a path, bytes, or file-like object."""

    def __init__(
        self,
        source: str | Path | bytes | BinaryIO | OfdPackage,
    ) -> None:
        if isinstance(source, OfdPackage):
            self._package = source.copy()
        elif isinstance(source, (str, Path)):
            self._package = OfdPackage.from_path(source)
        elif isinstance(source, bytes):
            self._package = OfdPackage.from_bytes(source)
        else:
            self._package = OfdPackage.from_stream(source)

        self._compress_types: dict[str, int] | None = None
        if not isinstance(source, OfdPackage):
            self._capture_compress_types(source)

        ofd_root = parse_root(self._package.read_bytes(OFD_XML_ENTRY))
        self._ofd_root = ofd_root
        self._metadata = _parse_docinfo(ofd_root)
        doc_root_path = _parse_doc_root(ofd_root)
        document_bytes = self._package.read_bytes(doc_root_path)
        document_root = parse_root(document_bytes)
        self._document = _parse_document(document_root, doc_root_path)
        self._pages: list[OfdPage] | None = None

    def _capture_compress_types(self, source: str | Path | bytes | BinaryIO) -> None:
        import io
        import zipfile

        try:
            if isinstance(source, (str, Path)):
                zf_ctx = zipfile.ZipFile(source, "r")
            elif isinstance(source, bytes):
                zf_ctx = zipfile.ZipFile(io.BytesIO(source), "r")
            else:
                source.seek(0)
                zf_ctx = zipfile.ZipFile(source, "r")
            with zf_ctx as zf:
                self._compress_types = {}
                for info in zf.infolist():
                    if not info.is_dir():
                        key = normalize_zip_path(info.filename)
                        self._compress_types[key] = info.compress_type
        except (OSError, zipfile.BadZipFile):
            self._compress_types = None

    @property
    def package(self) -> OfdPackage:
        """Underlying package (copy); for writer append."""
        return self._package.copy()

    @property
    def compress_types(self) -> dict[str, int] | None:
        """Per-entry compression from the original file, if available."""
        return self._compress_types.copy() if self._compress_types else None

    @property
    def metadata(self) -> dict[str, str]:
        """DocInfo fields from OFD.xml (mutable dict copy for inspection)."""
        return dict(self._metadata)

    @property
    def document(self) -> DocumentInfo:
        return self._document

    @property
    def doc_root(self) -> str:
        return self._document.doc_root

    @property
    def outlines(self) -> list[OutlineItem]:
        return list(self._document.outlines)

    @property
    def page_count(self) -> int:
        return len(self._document.pages)

    @property
    def pages(self) -> list[OfdPage]:
        if self._pages is None:
            self._pages = [
                OfdPage(self, ref) for ref in self._document.pages
            ]
        return self._pages

    def get_page(self, index: int) -> OfdPage:
        return self.pages[index]

    def extract_text(
        self,
        *,
        page_separator: str = "\n",
        skip_whitespace: bool = True,
    ) -> str:
        """Extract text from all pages."""
        parts = [
            page.extract_text(skip_whitespace=skip_whitespace)
            for page in self.pages
        ]
        return page_separator.join(parts)
