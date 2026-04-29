"""WordprocessingML / DrawingML XML 네임스페이스 및 qname 헬퍼."""

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "pic": "http://schemas.openxmlformats.org/drawingml/2006/picture",
    "xml": "http://www.w3.org/XML/1998/namespace",
}


def qn(tag: str) -> str:
    """`w:p` → `{http://...}p` (lxml/ElementTree에서 쓰는 Clark notation)."""
    prefix, local = tag.split(":", 1)
    return f"{{{NS[prefix]}}}{local}"


def w(local: str) -> str:
    return qn(f"w:{local}")
