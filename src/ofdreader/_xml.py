"""Namespace-aware XML helpers for OFD."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Iterator
from xml.etree.ElementTree import Element

from ofdreader._constants import OFD_NS, OFD_NS_TAG


def parse_root(data: bytes) -> Element:
    """Parse XML bytes and return the document root."""
    return ET.fromstring(data)


def to_bytes(root: Element, *, xml_declaration: bool = True) -> bytes:
    """Serialize an element tree to UTF-8 XML bytes."""
    if xml_declaration:
        ET.register_namespace("ofd", OFD_NS)
    body = ET.tostring(root, encoding="utf-8", xml_declaration=xml_declaration)
    return body


def local_name(tag: str) -> str:
    """Return the local part of a Clark notation tag."""
    if tag.startswith("{"):
        return tag.split("}", 1)[1]
    return tag


def is_ofd(tag: str, name: str) -> bool:
    return tag == f"{OFD_NS_TAG}{name}" or local_name(tag) == name


def find_child(parent: Element, name: str) -> Element | None:
    """Find the first direct child with the given OFD local name."""
    for child in parent:
        if is_ofd(child.tag, name):
            return child
    return None


def find_children(parent: Element, name: str) -> list[Element]:
    """Find all direct children with the given OFD local name."""
    return [child for child in parent if is_ofd(child.tag, name)]


def iter_descendants(parent: Element, name: str) -> Iterator[Element]:
    """Depth-first iteration over descendants with the given local name."""
    for elem in parent.iter():
        if elem is not parent and is_ofd(elem.tag, name):
            yield elem


def text_content(elem: Element | None) -> str:
    if elem is None:
        return ""
    return (elem.text or "").strip()


def get_attr(elem: Element, name: str, default: str | None = None) -> str | None:
    return elem.get(name, default)
