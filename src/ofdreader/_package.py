"""OFD ZIP container access."""

from __future__ import annotations

import io
import posixpath
import zipfile
from pathlib import Path, PurePosixPath
from typing import BinaryIO, Mapping

from ofdreader._constants import OFD_XML_ENTRY
from ofdreader.exceptions import OfdFormatError, OfdNotFoundError


def normalize_zip_path(path: str) -> str:
    """Normalize a path inside the OFD ZIP archive."""
    path = path.replace("\\", "/").strip()
    parts: list[str] = []
    for part in PurePosixPath(path).parts:
        if part in ("", "."):
            continue
        if part == "..":
            if parts:
                parts.pop()
            continue
        parts.append(part)
    return "/".join(parts)


def resolve_path(base: str, loc: str) -> str:
    """Resolve a relative location against a base directory in the package."""
    base = normalize_zip_path(base)
    loc = loc.strip()
    if not loc:
        return base
    if "/" not in base:
        return normalize_zip_path(posixpath.join(base, loc))
    base_dir = posixpath.dirname(base)
    if base_dir:
        return normalize_zip_path(posixpath.join(base_dir, loc))
    return normalize_zip_path(loc)


def doc_dir_for(doc_root: str) -> str:
    """Return the document directory (e.g. Doc_0) for a DocRoot path."""
    normalized = normalize_zip_path(doc_root)
    parent = posixpath.dirname(normalized)
    return parent or ""


class OfdPackage:
    """In-memory representation of an OFD ZIP package."""

    def __init__(self, entries: Mapping[str, bytes]) -> None:
        self._entries = dict(entries)
        if OFD_XML_ENTRY not in self._entries:
            raise OfdFormatError(f"Missing required entry: {OFD_XML_ENTRY}")

    @classmethod
    def from_path(cls, path: str | Path) -> OfdPackage:
        path = Path(path)
        if not path.is_file():
            raise OfdFormatError(f"Not a file: {path}")
        try:
            with zipfile.ZipFile(path, "r") as zf:
                return cls.from_zipfile(zf)
        except zipfile.BadZipFile as exc:
            raise OfdFormatError(f"Not a valid OFD/ZIP file: {path}") from exc

    @classmethod
    def from_bytes(cls, data: bytes) -> OfdPackage:
        buffer = io.BytesIO(data)
        try:
            with zipfile.ZipFile(buffer, "r") as zf:
                return cls.from_zipfile(zf)
        except zipfile.BadZipFile as exc:
            raise OfdFormatError("Not a valid OFD/ZIP buffer") from exc

    @classmethod
    def from_stream(cls, stream: BinaryIO) -> OfdPackage:
        try:
            with zipfile.ZipFile(stream, "r") as zf:
                return cls.from_zipfile(zf)
        except zipfile.BadZipFile as exc:
            raise OfdFormatError("Not a valid OFD/ZIP stream") from exc

    @classmethod
    def from_zipfile(cls, zf: zipfile.ZipFile) -> OfdPackage:
        entries: dict[str, bytes] = {}
        for info in zf.infolist():
            if info.is_dir():
                continue
            name = normalize_zip_path(info.filename)
            entries[name] = zf.read(info.filename)
        return cls(entries)

    @classmethod
    def from_directory(cls, directory: str | Path) -> OfdPackage:
        """Build a package from an extracted OFD directory tree."""
        directory = Path(directory)
        entries: dict[str, bytes] = {}
        for path in directory.rglob("*"):
            if path.is_file():
                rel = path.relative_to(directory).as_posix()
                entries[normalize_zip_path(rel)] = path.read_bytes()
        return cls(entries)

    def copy(self) -> OfdPackage:
        return OfdPackage(dict(self._entries))

    def list_entries(self) -> list[str]:
        return sorted(self._entries.keys())

    def has_entry(self, path: str) -> bool:
        return normalize_zip_path(path) in self._entries

    def read_bytes(self, path: str) -> bytes:
        key = normalize_zip_path(path)
        if key not in self._entries:
            raise OfdNotFoundError(f"Package entry not found: {path}")
        return self._entries[key]

    def read_text(self, path: str, encoding: str = "utf-8") -> str:
        return self.read_bytes(path).decode(encoding)

    def write_bytes(self, path: str, data: bytes) -> None:
        self._entries[normalize_zip_path(path)] = data

    def write_text(self, path: str, text: str, encoding: str = "utf-8") -> None:
        self.write_bytes(path, text.encode(encoding))

    def remove_entry(self, path: str) -> None:
        self._entries.pop(normalize_zip_path(path), None)

    def save(
        self,
        path: str | Path | BinaryIO,
        *,
        compress_types: Mapping[str, int] | None = None,
    ) -> None:
        """Write the package to a .ofd file or stream."""
        default_compress = zipfile.ZIP_STORED
        if isinstance(path, (str, Path)):
            with zipfile.ZipFile(path, "w") as zf:
                self._write_to_zip(zf, compress_types, default_compress)
        else:
            with zipfile.ZipFile(path, "w") as zf:
                self._write_to_zip(zf, compress_types, default_compress)

    def _write_to_zip(
        self,
        zf: zipfile.ZipFile,
        compress_types: Mapping[str, int] | None,
        default_compress: int,
    ) -> None:
        for name in sorted(self._entries.keys()):
            compress = default_compress
            if compress_types and name in compress_types:
                compress = compress_types[name]
            zf.writestr(
                zipfile.ZipInfo(filename=name),
                self._entries[name],
                compress_type=compress,
            )
