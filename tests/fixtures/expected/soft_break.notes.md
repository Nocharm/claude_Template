# soft_break.docx — Expected 해설

soft return(`<w:br/>`)과 hard return의 구분이 손실 없이 보존되는지 검증.

## 핵심 약속

- soft break는 paragraph를 분리하지 **않는다** (현 정책).
- 대신 `soft_breaks: list[int]` 가 위치를 보존한다 — 후속 로직이 분리 정책을 결정 가능.

## paragraph 1 (간단한 케이스)

- 입력: `"첫 번째 줄"<br/>"두 번째 줄"`
- 기대: `soft_breaks_count == 1`
- 후속에서 paragraph로 승격하려면:
  ```
  segments = split_runs_by_breaks(runs, soft_breaks)
  # → [["첫 번째 줄"], ["두 번째 줄"]]
  ```

## paragraph 4 (다중 break)

- 입력: 4 segments + 3 breaks
- 기대: `soft_breaks_count == 3`
- 위치 정보가 정확하면 4개 paragraph로 분리 가능.

## 후속 로직 주의

- soft break를 paragraph로 승격할 때, **원본 paragraph의 numbering/style/indent를 자식들에게 어떻게 상속시킬지** 정책 결정 필요.
  - 옵션 A: 첫 자식만 numbering 유지, 나머지는 일반 paragraph
  - 옵션 B: 모든 자식이 같은 numbering 공유 (하지만 워드 자동 번호는 paragraph마다 카운트되므로 부작용 가능)
- soft break 인덱스는 **runs 인덱스 기준**. 빈 run 또는 placeholder run이 끼어 있을 수 있음 → 텍스트 join 시 빈 run을 무시해도 무방.

## 알려진 구현 quirk

현 파서는 `<w:br/>`를 만나면 새 빈 run을 push한 뒤 break 위치를 그 run으로 마크함.
즉 `runs[soft_breaks[i]]` 가 **빈 텍스트 run** 일 수 있다.
의미적으로는 "soft break 직전" 위치 마커이며, 후속에서 split할 때 무시하면 됨.
