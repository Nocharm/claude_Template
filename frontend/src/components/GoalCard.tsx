import { Link } from "react-router-dom";

import type { Progress } from "../api";

interface GoalCardProps {
  progress: Progress;
}

/** Home-screen nudge: today's goal ring plus streak/level, both leading into study. */
export function GoalCard({ progress }: GoalCardProps) {
  const { answered, goal, goal_met } = progress.today;
  const percent = Math.min(100, (100 * answered) / goal);
  const remaining = Math.max(0, goal - answered);

  return (
    <Link
      to="/review"
      className="card card-link row"
      style={{ background: "var(--butter)", border: 0 }}
      data-testid="GoalCard-reviewLink"
    >
      <div
        className="goal-ring"
        style={{ background: `conic-gradient(var(--green) 0 ${percent}%, #fff ${percent}% 100%)` }}
      >
        <span>
          {answered}/{goal}
        </span>
      </div>
      <div style={{ flex: 1 }}>
        <div className="hand" style={{ fontSize: 22, lineHeight: 1.2 }}>
          {goal_met ? "오늘 도장 완료!" : `오늘 목표까지 ${remaining}개!`}
        </div>
        <div className="muted" style={{ color: "#5d4a12" }}>
          {goal_met ? "더 풀면 XP가 계속 쌓여요" : "달성하면 달력에 도장 + 30 XP"}
        </div>
      </div>
      <span className="number" style={{ color: "var(--green-dark)", fontSize: 13 }}>
        +{progress.today.xp_today} XP
      </span>
    </Link>
  );
}
