# ofdreader

**English** | [中文](README_zh.md)

**ofdreader** is a Python library for data extraction, analysis, conversion & manipulation of [OFD](https://www.gb688.cn/bzgk/gb/newGbInfo?hcno=7B5673888A4E432686E8A7BFCBBEA4C9) (Open Fixed-layout Document; China national standard GB/T 33190—2016) documents.

## Install

```bash
pip install ofdreader
```

Development:

```bash
pip install -e ".[dev]"
pytest
```

## Quick start

```python
from ofdreader import OfdReader, OfdWriter, ofd_to_pdf, ofd_to_pdf_layout

reader = OfdReader("document.ofd")
print(reader.metadata["Author"])
print(reader.page_count)

text = reader.pages[0].extract_text()
full_text = reader.extract_text()  # keeps paragraph breaks, joins line wraps
# flat = reader.extract_text(preserve_layout=False)  # single continuous string

writer = OfdWriter()
writer.append(reader)
writer.metadata["Author"] = "Updated Author"
writer.write("copy.ofd")

# Export current extracted paragraphs to a simple PDF
ofd_to_pdf("document.ofd", "document.txt-layout.pdf")

# Export with approximate original fonts/layout from OFD XML
ofd_to_pdf_layout("document.ofd", "document.layout.pdf")
```

Merge an extra page from another file:

```python
writer = OfdWriter()
writer.append(OfdReader("a.ofd"))
writer.append_pages(OfdReader("b.ofd"), pages=[0])
writer.write("merged.ofd")
```

## Scope (v0.1)

- Open `.ofd` packages (ZIP) from path, bytes, or file-like objects
- Read `DocInfo` metadata, page list, outlines
- Extract plain text from `TextObject` / `TextCode` (default keeps paragraph breaks, joins wrapped lines)
- Clone packages, update metadata, append pages across documents
- Export extracted text paragraphs to PDF (`ofd_to_pdf`, optional `reportlab`)
- Export approximate original layout PDF (`ofd_to_pdf_layout`)

Not included yet: full layout rendering, digital signatures, annotations, creating
new glyph-mapped text.

## Related projects

- [easyofd](https://pypi.org/project/easyofd/) — OFD ↔ PDF/image conversion
- PyPI name `pyofd` is a different library (tax receipt OFD providers)

## License

MIT — see [LICENSE](LICENSE).
