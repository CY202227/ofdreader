# ofdreader

[English](README.md) | **中文**

**ofdreader** 是一个用于 [OFD](https://www.gb688.cn/bzgk/gb/newGbInfo?hcno=7B5673888A4E432686E8A7BFCBBEA4C9)（开放式版式文档，中国国家标准 GB/T 33190—2016，国内电子公文与版式归档采用的固定版式文件格式）文档的数据提取、分析、转换与操作的 Python 库。

## 安装

```bash
pip install ofdreader
```

开发环境：

```bash
pip install -e ".[dev]"
pytest
```

## 快速开始

```python
from ofdreader import OfdReader, OfdWriter, ofd_to_pdf, ofd_to_pdf_layout

reader = OfdReader("document.ofd")
print(reader.metadata["Author"])
print(reader.page_count)

text = reader.pages[0].extract_text()
full_text = reader.extract_text()  # 保留段落换行，合并行内折行
# flat = reader.extract_text(preserve_layout=False)  # 连续单行文本

writer = OfdWriter()
writer.append(reader)
writer.metadata["Author"] = "Updated Author"
writer.write("copy.ofd")

# 将当前提取的段落文本导出为 PDF
ofd_to_pdf("document.ofd", "document.txt-layout.pdf")

# 按 OFD XML 尽可能保留原字体与版式导出
ofd_to_pdf_layout("document.ofd", "document.layout.pdf")
```

从另一个文件合并额外页面：

```python
writer = OfdWriter()
writer.append(OfdReader("a.ofd"))
writer.append_pages(OfdReader("b.ofd"), pages=[0])
writer.write("merged.ofd")
```

## 功能范围（v0.1）

- 从路径、字节或类文件对象打开 `.ofd` 包（ZIP）
- 读取 `DocInfo` 元数据、页面列表、大纲
- 从 `TextObject` / `TextCode` 提取纯文本（默认保留段落换行，合并行内折行）
- 克隆包、更新元数据、跨文档追加页面
- 将提取后的段落文本导出为 PDF（`ofd_to_pdf`，可选依赖 `reportlab`）
- 按原版式近似导出 PDF（`ofd_to_pdf_layout`）

尚未支持：完整版面渲染、数字签名、批注、创建新的字形映射文本。

## 相关项目

- [easyofd](https://pypi.org/project/easyofd/) — OFD ↔ PDF/图片转换
- PyPI 上的 `pyofd` 是另一个库（面向税务发票等 OFD 提供商）

## 许可证

MIT — 详见 [LICENSE](LICENSE)。
