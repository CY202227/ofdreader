"""OfdWriter: PyPDF2-style write API for OFD documents."""

from __future__ import annotations

import posixpath
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import BinaryIO
from xml.etree.ElementTree import Element, SubElement

from ofdreader._constants import OFD_NS_TAG, OFD_XML_ENTRY
from ofdreader._package import OfdPackage, doc_dir_for, normalize_zip_path, resolve_path
from ofdreader._xml import (
    find_child,
    find_children,
    get_attr,
    local_name,
    parse_root,
    text_content,
    to_bytes,
)
from ofdreader.exceptions import OfdFormatError, OfdNotFoundError, OfdWriteError
from ofdreader.models import PageRef
from ofdreader.reader import OfdReader, _parse_doc_root, _parse_document

class _MetadataDict(dict):
    """Dict that marks the parent writer dirty on mutation."""

    def __init__(self, writer: OfdWriter, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._writer = writer

    def __setitem__(self, key, value) -> None:
        super().__setitem__(key, value)
        self._writer._metadata_dirty = True


_DOCINFO_SIMPLE = frozenset({
    "DocID",
    "Title",
    "Author",
    "Subject",
    "Abstract",
    "CreationDate",
    "ModDate",
    "DocUsage",
    "Cover",
    "Keywords",
    "Creator",
    "CreatorVersion",
})


def _max_id_in_xml(data: bytes) -> int:
    """Scan XML for numeric ID attributes and return the maximum."""
    text = data.decode("utf-8", errors="ignore")
    ids = [int(m) for m in re.findall(r'\bID="(\d+)"', text)]
    return max(ids) if ids else 0


def _set_element_text(parent: Element, local: str, value: str) -> Element:
    tag = f"{OFD_NS_TAG}{local}"
    for child in list(parent):
        if child.tag == tag or local_name(child.tag) == local:
            child.text = value
            return child
    elem = SubElement(parent, tag)
    elem.text = value
    return elem


def _apply_metadata_to_ofd(ofd_root: Element, metadata: dict[str, str]) -> None:
    doc_body = find_child(ofd_root, "DocBody")
    if doc_body is None:
        raise OfdFormatError("OFD.xml missing DocBody")
    doc_info = find_child(doc_body, "DocInfo")
    if doc_info is None:
        doc_info = SubElement(doc_body, f"{OFD_NS_TAG}DocInfo")

    custom: dict[str, str] = {}
    for key, value in metadata.items():
        if key.startswith("CustomData:"):
            custom[key.split(":", 1)[1]] = value
            continue
        if key in _DOCINFO_SIMPLE:
            _set_element_text(doc_info, key, value)

    if custom:
        custom_datas = find_child(doc_info, "CustomDatas")
        if custom_datas is None:
            custom_datas = SubElement(doc_info, f"{OFD_NS_TAG}CustomDatas")
        for name, value in custom.items():
            tag = f"{OFD_NS_TAG}CustomData"
            found = None
            for child in find_children(custom_datas, "CustomData"):
                if get_attr(child, "Name") == name:
                    found = child
                    break
            if found is None:
                found = SubElement(custom_datas, tag)
                found.set("Name", name)
            found.text = value


class OfdWriter:
    """Build or modify an OFD package and write it to disk."""

    def __init__(self) -> None:
        self._package: OfdPackage | None = None
        self._document = None
        self._ofd_root: Element | None = None
        self._metadata: dict[str, str] = {}
        self._metadata_dirty = False
        self._compress_types: dict[str, int] | None = None

    @property
    def metadata(self) -> dict[str, str]:
        """Mutable DocInfo fields applied on write."""
        return self._metadata

    @metadata.setter
    def metadata(self, value: dict[str, str]) -> None:
        self._metadata = dict(value)
        self._metadata_dirty = True

    def append(self, reader: OfdReader) -> None:
        """Clone an entire OFD document into this writer (empty writer only)."""
        if self._package is not None:
            raise OfdWriteError(
                "Writer already has a document; use append_pages to merge pages."
            )
        self._package = reader.package
        self._compress_types = reader.compress_types
        self._ofd_root = parse_root(self._package.read_bytes(OFD_XML_ENTRY))
        doc_root_path = _parse_doc_root(self._ofd_root)
        document_root = parse_root(self._package.read_bytes(doc_root_path))
        self._document = _parse_document(document_root, doc_root_path)
        self._metadata = _MetadataDict(self, **reader.metadata)
        self._metadata_dirty = False

    def append_pages(
        self,
        reader: OfdReader,
        pages: list[int] | None = None,
    ) -> None:
        """Copy pages from another document into the current package."""
        if self._package is None or self._document is None:
            raise OfdWriteError("Call append() before append_pages().")

        src_doc = reader.document
        src_dir = src_doc.doc_dir
        tgt_doc = self._document
        tgt_dir = tgt_doc.doc_dir

        if pages is None:
            pages = list(range(reader.page_count))
        if not pages:
            return

        doc_root = parse_root(self._package.read_bytes(tgt_doc.doc_root))
        pages_elem = find_child(doc_root, "Pages")
        if pages_elem is None:
            raise OfdFormatError("Document.xml missing Pages")

        existing_ids = {p.page_id for p in tgt_doc.pages}
        next_page_id = max(existing_ids) if existing_ids else 0

        max_unit = tgt_doc.max_unit_id
        pages_dir = posixpath.join(tgt_dir, "Pages")

        for page_index in pages:
            if page_index < 0 or page_index >= len(src_doc.pages):
                raise OfdWriteError(f"Page index out of range: {page_index}")
            src_page = src_doc.pages[page_index]
            src_prefix_dir = posixpath.dirname(src_page.base_loc)

            next_page_id += 1
            new_page_dir_name = f"Page_{next_page_id - 1}"
            new_page_dir = posixpath.join(pages_dir, new_page_dir_name)
            new_content = posixpath.join(new_page_dir, "Content.xml")

            src_pkg = reader.package
            prefix = src_prefix_dir + "/"
            for entry in src_pkg.list_entries():
                if entry == src_page.base_loc:
                    self._package.write_bytes(
                        new_content, src_pkg.read_bytes(entry)
                    )
                    max_unit = max(
                        max_unit, _max_id_in_xml(src_pkg.read_bytes(entry))
                    )
                elif entry.startswith(prefix):
                    rel = entry[len(prefix) :]
                    tgt_path = posixpath.join(new_page_dir, rel)
                    self._package.write_bytes(
                        tgt_path, src_pkg.read_bytes(entry)
                    )
                    max_unit = max(
                        max_unit, _max_id_in_xml(src_pkg.read_bytes(entry))
                    )

            page_elem = SubElement(pages_elem, f"{OFD_NS_TAG}Page")
            page_elem.set("ID", str(next_page_id))
            rel_loc = posixpath.relpath(new_content, tgt_dir).replace("\\", "/")
            page_elem.text = rel_loc

            tgt_doc.pages.append(
                PageRef(
                    page_id=next_page_id,
                    base_loc=new_content,
                    index=len(tgt_doc.pages),
                )
            )

        common = find_child(doc_root, "CommonData")
        if common is not None:
            max_unit_elem = find_child(common, "MaxUnitID")
            new_max = max(max_unit, tgt_doc.max_unit_id) + 1
            if max_unit_elem is None:
                max_unit_elem = SubElement(common, f"{OFD_NS_TAG}MaxUnitID")
            max_unit_elem.text = str(new_max)
            tgt_doc.max_unit_id = new_max

        self._package.write_bytes(tgt_doc.doc_root, to_bytes(doc_root))

    def write(self, path: str | Path | BinaryIO) -> None:
        """Write the OFD package, applying metadata changes if any."""
        if self._package is None:
            raise OfdWriteError("No document loaded; call append() first.")

        if self._metadata_dirty or self._metadata:
            ofd_root = self._ofd_root
            if ofd_root is None:
                ofd_root = parse_root(self._package.read_bytes(OFD_XML_ENTRY))
            merged = dict(self._metadata)
            if "ModDate" not in merged:
                merged["ModDate"] = datetime.now(timezone.utc).strftime(
                    "%Y-%m-%dT%H:%M:%S%z"
                )
            _apply_metadata_to_ofd(ofd_root, merged)
            self._package.write_bytes(OFD_XML_ENTRY, to_bytes(ofd_root))
            self._metadata_dirty = False

        self._package.save(path, compress_types=self._compress_types)
