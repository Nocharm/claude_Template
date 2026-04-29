"""CLI: python -m docx_parser <input.docx> [-o out.json] [--pretty] [--raw-xml]."""

import argparse
import json
import sys
from pathlib import Path

from docx_parser.parser import parse_docx


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="docx_parser",
        description="Word(.docx) 구조를 손실 없이 JSON으로 추출합니다.",
    )
    parser.add_argument("input", type=Path, help="대상 .docx 파일 경로")
    parser.add_argument("-o", "--output", type=Path, default=None, help="JSON 저장 경로 (생략 시 stdout)")
    parser.add_argument("--pretty", action="store_true", help="들여쓰기 적용")
    parser.add_argument("--raw-xml", action="store_true", help="단락 raw_xml 포함 (디버깅용)")
    args = parser.parse_args(argv)

    if not args.input.exists():
        print(f"파일이 없습니다: {args.input}", file=sys.stderr)
        return 2
    if args.input.suffix.lower() != ".docx":
        print(f"확장자가 .docx가 아닙니다: {args.input}", file=sys.stderr)
        return 2

    try:
        result = parse_docx(args.input, include_raw_xml=args.raw_xml)
    except Exception as e:  # noqa: BLE001 — 사용자 친화 메시지로 변환
        print(f"파싱 실패: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    indent = 2 if args.pretty else None
    text = json.dumps(result, ensure_ascii=False, indent=indent)

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
        print(f"저장 완료: {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(text)
        if indent is not None:
            sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
