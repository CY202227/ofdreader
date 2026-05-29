# ofdreader

**ofdreader** is a Python library for data extraction, analysis, conversion & manipulation of [OFD](https://www.ofdspec.org/) (and other) documents (GB/T 33190—2016). It provides a **PyPDF2-like** read/write API.

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
from ofdreader import OfdReader, OfdWriter

reader = OfdReader("document.ofd")
print(reader.metadata["Author"])
print(reader.page_count)

text = reader.pages[0].extract_text()
full_text = reader.extract_text()

writer = OfdWriter()
writer.append(reader)
writer.metadata["Author"] = "Updated Author"
writer.write("copy.ofd")
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
- Extract plain text from `TextObject` / `TextCode`
- Clone packages, update metadata, append pages across documents

Not included yet: rendering, PDF export, digital signatures, annotations, creating new glyph-mapped text.

## Related projects

- [easyofd](https://pypi.org/project/easyofd/) — OFD ↔ PDF/image conversion
- PyPI name `pyofd` is a different library (tax receipt OFD providers)

## License

MIT — see [LICENSE](LICENSE).
