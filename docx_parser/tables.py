"""표(Table) 추출. 셀 병합, 셀 내 단락 구조 보존."""

from docx_parser.ns import qn


def extract_table(
    tbl_elem,
    table_index: int,
    anchor_paragraph_index: int,
    para_extractor,
) -> dict:
    """w:tbl → 표 dict. 셀 내 단락은 para_extractor(p_elem)로 추출.

    para_extractor: extract_paragraph 부분 적용 함수 (index는 표 내부에서 새로 매김).
    """
    rows_data: list[list[dict]] = []
    merged_cells: list[dict] = []
    cell_para_index = 0

    rows = tbl_elem.findall(qn("w:tr"))
    n_rows = len(rows)
    n_cols = 0

    for row_idx, tr in enumerate(rows):
        cells_in_row: list[dict] = []
        col_cursor = 0
        for tc in tr.findall(qn("w:tc")):
            tcPr = tc.find(qn("w:tcPr"))
            grid_span = 1
            v_merge = None
            if tcPr is not None:
                gs = tcPr.find(qn("w:gridSpan"))
                if gs is not None:
                    grid_span = int(gs.get(qn("w:val")) or "1")
                vm = tcPr.find(qn("w:vMerge"))
                if vm is not None:
                    v_merge = vm.get(qn("w:val")) or "continue"  # 'restart' or 'continue'

            paragraphs_in_cell: list[dict] = []
            for p in tc.findall(qn("w:p")):
                paragraphs_in_cell.append(para_extractor(p, cell_para_index))
                cell_para_index += 1

            cell = {
                "row": row_idx,
                "col": col_cursor,
                "grid_span": grid_span,
                "v_merge": v_merge,
                "paragraphs": paragraphs_in_cell,
            }
            cells_in_row.append(cell)

            if grid_span > 1 or v_merge is not None:
                merged_cells.append({
                    "row": row_idx,
                    "col": col_cursor,
                    "grid_span": grid_span,
                    "v_merge": v_merge,
                })
            col_cursor += grid_span

        n_cols = max(n_cols, col_cursor)
        rows_data.append(cells_in_row)

    return {
        "index": table_index,
        "anchor_paragraph_index": anchor_paragraph_index,
        "rows": n_rows,
        "cols": n_cols,
        "merged_cells": merged_cells,
        "cells": rows_data,
        "caption": None,
    }
