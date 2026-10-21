import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api } from "../api";
import { Highlighted } from "../components/Highlighted";
import { Icon } from "../components/Icon";
import { SentenceCard } from "../components/SentenceCard";
import { setLastDayId } from "../lib/storage";
import { useApi } from "../lib/useApi";

type Mode = "passage" | "cards";

export function ReaderPage() {
  const dayId = Number(useParams().dayId);
  const [mode, setMode] = useState<Mode>("passage");
  const { data: day, error } = useApi(() => api.getDay(dayId), [dayId]);

  useEffect(() => {
    if (day) setLastDayId(day.id);
  }, [day]);

  if (error) return <main className="page error">{error.message}</main>;
  if (!day) return <main className="page muted">불러오는 중…</main>;

  const marks = day.sentences.flatMap((s) => s.expressions);

  return (
    <main className="page" data-testid="ReaderPage-main">
      <div className="spread">
        <Link to="/" className="icon-button" aria-label="홈으로" data-testid="ReaderPage-backLink">
          <Icon name="back" />
        </Link>
        <div className="segmented" role="group" aria-label="보기 방식">
          <button
            type="button"
            aria-pressed={mode === "passage"}
            onClick={() => setMode("passage")}
            data-testid="ReaderPage-passageModeButton"
          >
            원문
          </button>
          <button
            type="button"
            aria-pressed={mode === "cards"}
            onClick={() => setMode("cards")}
            data-testid="ReaderPage-cardsModeButton"
          >
            문장 카드
          </button>
        </div>
        <span style={{ width: 44 }} />
      </div>

      <div className="row">
        <div className="day-tag">
          <small>DAY</small>
          <strong>{day.day_no}</strong>
        </div>
        <h1 className="title" style={{ fontSize: 22 }}>
          {day.title}
        </h1>
      </div>

      {mode === "passage" ? (
        <>
          <div className="ruled" data-testid="ReaderPage-passage">
            <Highlighted text={day.passage_en} marks={marks} isLinked />
          </div>
          <p className="muted">형광펜을 누르면 설명이 열려요</p>
        </>
      ) : (
        <div className="stack" style={{ gap: 20 }} data-testid="ReaderPage-cards">
          {day.sentences.map((sentence) => (
            <SentenceCard key={sentence.id} sentence={sentence} />
          ))}
        </div>
      )}

      <Link to={`/map?day=${day.id}`} className="button secondary" data-testid="ReaderPage-mapLink">
        DAY {day.day_no} 표현 맵
      </Link>

      <div className="spread">
        {day.prev_day_id ? (
          <Link
            to={`/days/${day.prev_day_id}`}
            className="button secondary"
            data-testid="ReaderPage-prevLink"
          >
            <Icon name="back" size={18} />
            이전 DAY
          </Link>
        ) : (
          <span />
        )}
        {day.next_day_id && (
          <Link
            to={`/days/${day.next_day_id}`}
            className="button"
            data-testid="ReaderPage-nextLink"
          >
            다음 DAY
            <Icon name="forward" size={18} />
          </Link>
        )}
      </div>
    </main>
  );
}
