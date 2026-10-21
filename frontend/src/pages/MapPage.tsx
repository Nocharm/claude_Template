import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { api, RELATION_LABELS, type ExpressionDetail, type Related } from "../api";
import { getLastDayId } from "../lib/storage";
import { useApi } from "../lib/useApi";

/** Pair neighbours into left/right rows hanging off the central spine. */
function pairRows(related: Related[]): [Related, Related | null][] {
  const rows: [Related, Related | null][] = [];
  for (let i = 0; i < related.length; i += 2) rows.push([related[i], related[i + 1] ?? null]);
  return rows;
}

function nodeLabel(related: Related): string {
  return related.type === "sense" ? related.meaning_ko : related.text;
}

export function MapPage() {
  const [params] = useSearchParams();
  const expressionId = Number(params.get("expression")) || null;
  const dayId = Number(params.get("day")) || getLastDayId();

  return (
    <main className="page" data-testid="MapPage-main">
      <h1 className="title">표현 맵</h1>
      {expressionId ? (
        <EgoGraph expressionId={expressionId} />
      ) : dayId ? (
        <CenterPicker dayId={dayId} />
      ) : (
        <p className="muted">먼저 DAY를 하나 읽어 보세요.</p>
      )}
    </main>
  );
}

function CenterPicker({ dayId }: { dayId: number }) {
  const { data: day, error } = useApi(() => api.getDay(dayId), [dayId]);
  if (error) return <p className="error">{error.message}</p>;
  if (!day) return <p className="muted">불러오는 중…</p>;

  return (
    <section className="stack" data-testid="MapPage-centerPicker">
      <p className="muted" style={{ margin: 0 }}>
        DAY {day.day_no}에서 중심 표현을 골라요
      </p>
      <div className="wrap">
        {day.sentences
          .flatMap((s) => s.expressions)
          .map((expression) => (
            <Link
              key={expression.id}
              to={`/map?expression=${expression.id}`}
              className="chip"
              data-testid={`MapPage-center-${expression.id}`}
            >
              <span className="hand" style={{ fontSize: 19 }}>
                {expression.text}
              </span>
            </Link>
          ))}
      </div>
    </section>
  );
}

function EgoGraph({ expressionId }: { expressionId: number }) {
  const { data: center, error } = useApi(() => api.getExpression(expressionId), [expressionId]);
  if (error) return <p className="error">{error.message}</p>;
  if (!center) return <p className="muted">불러오는 중…</p>;
  // Remount on center change so the selection resets to the new first neighbour.
  return <EgoGraphView key={center.id} center={center} />;
}

function EgoGraphView({ center }: { center: ExpressionDetail }) {
  const [selected, setSelected] = useState<Related | null>(center.related[0] ?? null);
  const nodeKey = (r: Related) => `${r.type}-${r.id}`;

  function renderNode(related: Related) {
    const isSelected = selected !== null && nodeKey(selected) === nodeKey(related);
    return (
      <button
        type="button"
        className="map-node"
        aria-pressed={isSelected}
        onClick={() => setSelected(related)}
        data-testid={`MapPage-node-${related.id}`}
      >
        <span className={`tag tag-${related.type}`}>
          {RELATION_LABELS[related.type]}
          {related.day_no !== center.day_no && ` · DAY ${related.day_no}`}
        </span>
        {nodeLabel(related)}
      </button>
    );
  }

  return (
    <>
      <div className="map" data-testid="MapPage-graph">
        <Link
          to={`/expressions/${center.id}`}
          className="map-center"
          data-testid="MapPage-centerNode"
        >
          {center.text}
        </Link>
        {center.related.length === 0 && (
          <p className="muted" style={{ marginBottom: 0 }}>
            아직 연결된 표현이 없어요
          </p>
        )}
        {pairRows(center.related).map(([left, right]) => (
          <div className="map-row" key={nodeKey(left)}>
            {renderNode(left)}
            <div className="map-stub" />
            {right ? <div className="map-stub" /> : <div />}
            {right ? renderNode(right) : <div />}
          </div>
        ))}
      </div>

      {selected && (
        <section
          className="card stack"
          style={{ border: "2px solid var(--tangerine)" }}
          data-testid="MapPage-selectedCard"
        >
          <div className="spread">
            <strong>{nodeLabel(selected)}</strong>
            <span className={`tag tag-${selected.type}`}>{RELATION_LABELS[selected.type]}</span>
          </div>
          <span className="muted">{selected.note || selected.meaning_ko}</span>
          <div className="wrap">
            <Link
              to={`/expressions/${selected.id}`}
              className="button secondary"
              data-testid="MapPage-detailLink"
            >
              자세히
            </Link>
            <Link
              to={`/map?expression=${selected.id}`}
              className="button"
              data-testid="MapPage-recenterLink"
            >
              이 표현을 중심으로
            </Link>
          </div>
        </section>
      )}
    </>
  );
}
