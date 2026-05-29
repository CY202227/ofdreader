"""OFD reader/writer exceptions."""


class OfdError(Exception):
    """Base exception for ofdreader."""


class OfdFormatError(OfdError):
    """Raised when the file is not a valid OFD package."""


class OfdNotFoundError(OfdError):
    """Raised when a required entry or XML element is missing."""


class OfdWriteError(OfdError):
    """Raised when writing or merging OFD packages fails."""
