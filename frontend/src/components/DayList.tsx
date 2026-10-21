import { Link } from "react-router-dom";

import { api } from "../api";
import { useApi } from "../lib/useApi";

interface DayListProps {
  bookId: number;
}

export function DayList({ bookId }: DayListProps) {
  const { data: days, error } = useApi(() => api.listDays(bookId), [bookId]);

  if (error) return <p className="error">{error.message}</p>;
  if (!days) return <p className="muted">불러오는 중…</p>;

  return (
    <div className="stack" data-testid={`DayList-list-${bookId}`}>
      {days.map((day) => (
        <Link
          key={day.id}
          to={`/days/${day.id}`}
          className="card card-link row"
          data-testid={`DayList-item-${day.id}`}
        >
          <div className="day-tag">
            <small>DAY</small>
            <strong>{day.day_no}</strong>
          </div>
          <div>
            <div className="hand" style={{ fontSize: 21, lineHeight: 1.2 }}>
              {day.title}
            </div>
            <div className="muted">표현 {day.expression_count}개</div>
          </div>
        </Link>
      ))}
    </div>
  );
}
