"""Tests for OfdReader."""

from __future__ import annotations

from pathlib import Path

import pytest

from ofdreader import OfdFormatError, OfdReader
from ofdreader._package import OfdPackage


def test_open_invalid_file(tmp_path: Path) -> None:
    bad = tmp_path / "not.ofd"
    bad.write_text("not a zip", encoding="utf-8")
    with pytest.raises(OfdFormatError):
        OfdReader(bad)


def test_reader_metadata(sample_ofd_path: Path) -> None:
    reader = OfdReader(sample_ofd_path)
    assert reader.metadata["Author"] == "Lenovo"
    assert reader.metadata["Creator"] == "suwell-pdf2ofd"
    assert "86919700" in reader.metadata["DocID"]


def test_page_count(sample_ofd_path: Path) -> None:
    reader = OfdReader(sample_ofd_path)
    assert reader.page_count == 2
    assert len(reader.pages) == 2


def test_extract_text_page0(sample_ofd_path: Path) -> None:
    reader = OfdReader(sample_ofd_path)
    text = reader.pages[0].extract_text()
    assert "弘扬优良传统" in text
    assert "陈吉宁" in text


def test_extract_text_full(sample_ofd_path: Path) -> None:
    reader = OfdReader(sample_ofd_path)
    full = reader.extract_text()
    assert "弘扬优良传统" in full
    assert "解冬参加" in full


def test_outlines(sample_ofd_path: Path) -> None:
    reader = OfdReader(sample_ofd_path)
    assert len(reader.outlines) == 1
    assert "陈吉宁" in reader.outlines[0].title
    assert reader.outlines[0].page_id == 1


def test_from_directory(xml_only_dir: Path) -> None:
    package = OfdPackage.from_directory(xml_only_dir)
    reader = OfdReader(package)
    assert reader.page_count == 2


def test_from_bytes(sample_ofd_path: Path) -> None:
    data = sample_ofd_path.read_bytes()
    reader = OfdReader(data)
    assert reader.page_count == 2
