import { useEffect, useState, type ChangeEvent } from "react";
import { Link } from "react-router-dom";

import { api, type Book } from "../api";
import { DayList } from "../components/DayList";
import { GoalCard } from "../components/GoalCard";
import { getLastDayId } from "../lib/storage";
import { useApi } from "../lib/useApi";

// Poll interval while a book is being processed; ingest takes minutes, so seconds is plenty.
const POLL_MS = 3000;

const STATUS_LABELS: Record<Book["status"], string> = {
  queued: "대기 중",
  classifying: "페이지 살펴보는 중",
  extracting: "DAY별로 정리하는 중",
  linking: "표현끼리 연결하는 중",
  done: "완료",
  failed: "실패",
};

function isProcessing(book: Book): boolean {
  return book.status !== "done" && book.status !== "failed";
}

export function HomePage() {
  const [refreshKey, setRefreshKey] = useState(0);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const { data: books, error } = useApi(api.listBooks, [refreshKey]);
  const { data: progress } = useApi(api.getProgress, []);
  const lastDayId = getLastDayId();
  const { data: lastDay } = useApi(
    () => (lastDayId ? api.getDay(lastDayId) : Promise.resolve(null)),
    [lastDayId],
  );

  const hasProcessing = books?.some(isProcessing) ?? false;
  useEffect(() => {
    if (!hasProcessing) return;
    const timer = setInterval(() => setRefreshKey((key) => key + 1), POLL_MS);
    return () => clearInterval(timer);
  }, [hasProcessing]);

  async function handleUpload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setIsUploading(true);
    setUploadError(null);
    try {
      await api.uploadBook(file);
      setRefreshKey((key) => key + 1);
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsUploading(false);
    }
  }

  async function handleRetry(bookId: number) {
    try {
      await api.retryBook(bookId);
      setRefreshKey((key) => key + 1);
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : String(err));
    }
  }

  const today = new Date().toLocaleDateString("ko-KR", {
    month: "long",
    day: "numeric",
    weekday: "long",
  });

  return (
    <main className="page">
      <header className="spread" style={{ alignItems: "flex-end" }}>
        <div>
          <div className="muted">{today}</div>
          <h1 className="title">오늘의 노트</h1>
        </div>
        {progress && (
          <Link to="/progress" className="pill" data-testid="HomePage-progressLink">
            {progress.streak_days}일 연속 · Lv.{progress.level}
          </Link>
        )}
      </header>

      {progress && <GoalCard progress={progress} />}

      {lastDay && (
        <Link
          to={`/days/${lastDay.id}`}
          className="card card-link stack"
          data-testid="HomePage-continueLink"
        >
          <span className="eyebrow" style={{ color: "var(--green)" }}>
            이어 읽기
          </span>
          <div className="row">
            <div className="day-tag">
              <small>DAY</small>
              <strong>{lastDay.day_no}</strong>
            </div>
            <span className="hand" style={{ fontSize: 22, lineHeight: 1.2 }}>
              {lastDay.title}
            </span>
          </div>
        </Link>
      )}

      {error && <p className="error">{error.message}</p>}

      {books?.map((book) => (
        <section key={book.id} className="stack" data-testid={`HomePage-book-${book.id}`}>
          <div className="spread">
            <h2 className="title" style={{ fontSize: 18 }}>
              {book.title}
            </h2>
            {book.page_count && <span className="muted">{book.page_count}쪽</span>}
          </div>
          {book.status === "done" && <DayList bookId={book.id} />}
          {isProcessing(book) && (
            <div className="card stack" data-testid={`HomePage-progress-${book.id}`}>
              <div className="spread">
                <span>{STATUS_LABELS[book.status]}</span>
                {book.progress_total > 0 && (
                  <span className="number">
                    {book.progress_done} / {book.progress_total}
                  </span>
                )}
              </div>
              <div className="progress">
                <div
                  style={{
                    width: `${book.progress_total ? (100 * book.progress_done) / book.progress_total : 5}%`,
                  }}
                />
              </div>
              <span className="muted">책 한 권은 한 번만 처리돼요. 앱을 닫아도 계속 진행돼요.</span>
            </div>
          )}
          {book.status === "failed" && (
            <div className="error stack" data-testid={`HomePage-failed-${book.id}`}>
              <span>처리 실패: {book.error}</span>
              <button
                type="button"
                className="button secondary"
                onClick={() => handleRetry(book.id)}
                data-testid={`HomePage-retryButton-${book.id}`}
              >
                이어서 다시 처리
              </button>
            </div>
          )}
        </section>
      ))}

      <label className="button secondary" data-testid="HomePage-uploadLabel">
        {isUploading ? "올리는 중…" : "책 PDF 추가"}
        <input
          type="file"
          accept="application/pdf"
          hidden
          disabled={isUploading}
          onChange={handleUpload}
          data-testid="HomePage-uploadInput"
        />
      </label>
      {uploadError && <p className="error">{uploadError}</p>}
    </main>
  );
}
