"""Data extraction, analysis, conversion & manipulation of OFD (China GB/T 33190) documents."""

from ofdreader.exceptions import (
    OfdError,
    OfdFormatError,
    OfdNotFoundError,
    OfdWriteError,
)
from ofdreader.convert import ofd_to_pdf, ofd_to_pdf_layout
from ofdreader.reader import OfdPage, OfdReader
from ofdreader.writer import OfdWriter

__all__ = [
    "OfdError",
    "OfdFormatError",
    "OfdNotFoundError",
    "OfdPage",
    "OfdReader",
    "OfdWriteError",
    "OfdWriter",
    "ofd_to_pdf",
    "ofd_to_pdf_layout",
]

__version__ = "0.1.0"
