import { useState } from "react";
import { Link } from "react-router-dom";

import { api, type Daily, type Grade } from "../api";
import { QuizCard } from "../components/QuizCard";
import { StampOverlay } from "../components/StampOverlay";
import { useApi } from "../lib/useApi";

export function ReviewPage() {
  const [session, setSession] = useState(0);
  const [index, setIndex] = useState(0);
  const [daily, setDaily] = useState<Daily | null>(null);
  const [xpPop, setXpPop] = useState<{ key: number; amount: number } | null>(null);
  const [stampXp, setStampXp] = useState<number | null>(null);
  const [gradeError, setGradeError] = useState<string | null>(null);
  const { data: queue, error } = useApi(api.getQueue, [session]);

  if (error) return <main className="page error">{error.message}</main>;
  if (!queue) return <main className="page muted">불러오는 중…</main>;

  const items = queue.items;
  const today = daily ?? queue.today;
  const item = items[index];

  async function handleGrade(expressionId: number, grade: Grade) {
    try {
      const result = await api.gradeCard(expressionId, grade);
      setDaily(result.today);
      if (result.xp_gained > 0) setXpPop({ key: Date.now(), amount: result.xp_gained });
      if (result.goal_just_met) setStampXp(result.xp_gained);
      setGradeError(null);
      setIndex((i) => i + 1);
    } catch (err) {
      setGradeError(err instanceof Error ? err.message : String(err));
    }
  }

  function startAnotherRound() {
    setIndex(0);
    setSession((s) => s + 1);
  }

  return (
    <main className="page" data-testid="ReviewPage-main">
      <div className="spread">
        <h1 className="title">복습</h1>
        <span className="number" data-testid="ReviewPage-goalCount">
          오늘 {today.answered} / {today.goal}
        </span>
      </div>
      <div className="progress" aria-hidden="true">
        <div
          style={{
            width: `${Math.min(100, (100 * today.answered) / today.goal)}%`,
            background: "var(--tangerine)",
          }}
        />
      </div>

      {item ? (
        <>
          <span className="muted">
            {index + 1} / {items.length}
          </span>
          <QuizCard
            key={`${session}-${index}`}
            item={item}
            onCheck={(answer) => api.checkAnswer(item.expression_id, answer)}
            onGrade={(grade) => handleGrade(item.expression_id, grade)}
          />
        </>
      ) : (
        <section className="card stack" style={{ alignItems: "center", textAlign: "center" }}>
          <span className="hand" style={{ fontSize: 30 }}>
            {items.length ? "이번 복습 끝!" : "지금은 복습할 카드가 없어요"}
          </span>
          <span className="muted">
            {today.goal_met
              ? "오늘 도장은 이미 찍혔어요."
              : `목표까지 ${Math.max(0, today.goal - today.answered)}개 남았어요.`}
          </span>
          <div className="wrap" style={{ justifyContent: "center" }}>
            <button
              type="button"
              className="button secondary"
              onClick={startAnotherRound}
              data-testid="ReviewPage-moreButton"
            >
              더 풀기
            </button>
            <Link to="/progress" className="button" data-testid="ReviewPage-progressLink">
              달력 보기
            </Link>
          </div>
        </section>
      )}

      {gradeError && <p className="error">{gradeError}</p>}
      {xpPop && stampXp === null && (
        <span key={xpPop.key} className="xp-pop" aria-live="polite">
          +{xpPop.amount} XP
        </span>
      )}
      {stampXp !== null && <StampOverlay xpBonus={stampXp} onClose={() => setStampXp(null)} />}
    </main>
  );
}
