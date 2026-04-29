"""docx → JSON 구조 추출 파서. SOP 문서의 원본 구조를 손실 없이 보존한다."""

from docx_parser.parser import parse_docx

__all__ = ["parse_docx"]
