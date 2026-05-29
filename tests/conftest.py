"""Pytest fixtures for ofdreader."""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
SAMPLE_OFD = FIXTURES / "sample.ofd"
EXTRACTED_SRC = ROOT / "弘扬优良传统测试副本"
XML_ONLY = FIXTURES / "xml_only"


@pytest.fixture(scope="session")
def sample_ofd_path() -> Path:
    """Path to a .ofd file built from the repository sample tree."""
    if not SAMPLE_OFD.is_file():
        FIXTURES.mkdir(parents=True, exist_ok=True)
        if not EXTRACTED_SRC.is_dir():
            pytest.skip("Sample OFD tree not found")
        with zipfile.ZipFile(SAMPLE_OFD, "w", compression=zipfile.ZIP_STORED) as zf:
            for path in EXTRACTED_SRC.rglob("*"):
                if path.is_file():
                    zf.write(path, path.relative_to(EXTRACTED_SRC).as_posix())
    return SAMPLE_OFD


@pytest.fixture(scope="session")
def xml_only_dir() -> Path:
    """Extracted XML-only fixture directory."""
    if not XML_ONLY.is_dir():
        if not EXTRACTED_SRC.is_dir():
            pytest.skip("Sample OFD tree not found")
        shutil.copytree(EXTRACTED_SRC, XML_ONLY)
    return XML_ONLY
