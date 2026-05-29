"""Tests for OfdWriter."""

from __future__ import annotations

from pathlib import Path

import pytest

from ofdreader import OfdReader, OfdWriter, OfdWriteError


def test_round_trip(sample_ofd_path: Path, tmp_path: Path) -> None:
    reader = OfdReader(sample_ofd_path)
    out = tmp_path / "roundtrip.ofd"
    writer = OfdWriter()
    writer.append(reader)
    writer.write(out)

    again = OfdReader(out)
    assert again.page_count == reader.page_count
    assert again.extract_text() == reader.extract_text()
    assert again.metadata["Author"] == reader.metadata["Author"]


def test_metadata_update(sample_ofd_path: Path, tmp_path: Path) -> None:
    reader = OfdReader(sample_ofd_path)
    out = tmp_path / "meta.ofd"
    writer = OfdWriter()
    writer.append(reader)
    writer.metadata["Author"] = "Test Author"
    writer.write(out)

    again = OfdReader(out)
    assert again.metadata["Author"] == "Test Author"


def test_append_twice_raises(sample_ofd_path: Path) -> None:
    reader = OfdReader(sample_ofd_path)
    writer = OfdWriter()
    writer.append(reader)
    with pytest.raises(OfdWriteError):
        writer.append(reader)


def test_append_pages_merge(sample_ofd_path: Path, tmp_path: Path) -> None:
    reader = OfdReader(sample_ofd_path)
    out = tmp_path / "merged.ofd"

    writer = OfdWriter()
    writer.append(reader)
    writer.append_pages(reader, pages=[1])
    writer.write(out)

    merged = OfdReader(out)
    assert merged.page_count == 3
    assert "解冬参加" in merged.extract_text()


def test_write_without_append_raises(tmp_path: Path) -> None:
    writer = OfdWriter()
    with pytest.raises(OfdWriteError):
        writer.write(tmp_path / "empty.ofd")
