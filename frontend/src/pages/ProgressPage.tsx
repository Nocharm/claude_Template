import { useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../api";
import { Icon } from "../components/Icon";
import { useApi } from "../lib/useApi";

const WEEKDAYS = ["일", "월", "화", "수", "목", "금", "토"];

function shiftMonth(month: string, delta: number): string {
  const [year, mon] = month.split("-").map(Number);
  const shifted = new Date(year, mon - 1 + delta, 1);
  return `${shifted.getFullYear()}-${String(shifted.getMonth() + 1).padStart(2, "0")}`;
}

export function ProgressPage() {
  const [month, setMonth] = useState<string | undefined>(undefined);
  const { data: progress, error } = useApi(() => api.getProgress(month), [month]);

  if (error) return <main className="page error">{error.message}</main>;
  if (!progress) return <main className="page muted">불러오는 중…</main>;

  const [year, mon] = progress.month.split("-").map(Number);
  const leadingBlanks = new Date(year, mon - 1, 1).getDay();
  const levelPercent = (100 * progress.xp_into_level) / progress.xp_for_next;

  return (
    <main className="page" data-testid="ProgressPage-main">
      <div className="row" style={{ gap: 4 }}>
        <Link
          to="/"
          className="icon-button"
          aria-label="홈으로"
          data-testid="ProgressPage-backLink"
        >
          <Icon name="back" />
        </Link>
        <h1 className="title">나의 학습 노트</h1>
      </div>

      <section className="level-card" data-testid="ProgressPage-level">
        <div className="spread">
          <div className="row" style={{ gap: 8, alignItems: "baseline" }}>
            <span className="number" style={{ fontSize: 28, color: "var(--butter)" }}>
              Lv.{progress.level}
            </span>
            <span className="hand" style={{ fontSize: 20 }}>
              {progress.level_name}
            </span>
          </div>
        </div>
        <div className="progress">
          <div style={{ width: `${levelPercent}%` }} />
        </div>
        <span style={{ fontSize: 12, color: "#c9d1cd" }}>
          {progress.xp_into_level} / {progress.xp_for_next} XP · 누적 {progress.xp_total} XP
        </span>
      </section>

      <div className="tiles">
        <div
          className="tile"
          style={{ background: "var(--peach)", color: "var(--tangerine-dark)" }}
        >
          <span className="number">{progress.streak_days}</span>연속 일수
        </div>
        <div className="tile" style={{ background: "var(--marker)", color: "var(--green-dark)" }}>
          <span className="number">{progress.mastered}</span>마스터 표현
        </div>
        <div className="tile" style={{ background: "var(--sky)", color: "#1d4f6b" }}>
          <span className="number">
            {progress.calendar.filter((d) => d.status === "met").length}
          </span>
          이달 도장
        </div>
      </div>

      <section className="card stack" data-testid="ProgressPage-calendar">
        <div className="spread">
          <button
            type="button"
            className="icon-button"
            aria-label="이전 달"
            onClick={() => setMonth(shiftMonth(progress.month, -1))}
            data-testid="ProgressPage-prevMonthButton"
          >
            <Icon name="back" size={20} />
          </button>
          <span className="hand" style={{ fontSize: 22 }}>
            {year}년 {mon}월
          </span>
          <button
            type="button"
            className="icon-button"
            aria-label="다음 달"
            onClick={() => setMonth(shiftMonth(progress.month, 1))}
            data-testid="ProgressPage-nextMonthButton"
          >
            <Icon name="forward" size={20} />
          </button>
        </div>
        <div className="calendar">
          {WEEKDAYS.map((w) => (
            <div key={w} className="calendar-head">
              {w}
            </div>
          ))}
          {Array.from({ length: leadingBlanks }, (_, i) => (
            <div key={`blank-${i}`} />
          ))}
          {progress.calendar.map((day) => {
            const dayNo = Number(day.date.slice(8));
            const isToday = day.date === progress.today.date;
            return (
              <div
                key={day.date}
                className={`calendar-day ${day.status}${isToday ? " today" : ""}`}
                data-testid={`ProgressPage-day-${day.date}`}
              >
                {day.status === "met" ? <span className="stamp-mini">{dayNo}</span> : dayNo}
                {day.status === "partial" && <span className="dot" />}
              </div>
            );
          })}
        </div>
        <span className="muted">도장 = 목표 달성 · 점 = 조금 학습 · 하늘색 = 쉼표(주 1회)</span>
      </section>
    </main>
  );
}
