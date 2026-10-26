import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api, type ComicSummary } from "../api";
import { useApi } from "../lib/useApi";

// Drawing 10 panels takes minutes; a few seconds between polls is plenty.
const POLL_MS = 4000;

const STATUS_LABELS: Record<ComicSummary["status"], string> = {
  queued: "대기 중",
  writing: "콘티 쓰는 중",
  drawing: "그리는 중",
  done: "완성",
  failed: "실패",
};

function isActive(comic: ComicSummary): boolean {
  return comic.status !== "done" && comic.status !== "failed";
}

export function ComicsPage() {
  const [refreshKey, setRefreshKey] = useState(0);
  const [actionError, setActionError] = useState<string | null>(null);
  const { data: comics, error } = useApi(api.listComics, [refreshKey]);

  const hasActive = comics?.some(isActive) ?? false;
  useEffect(() => {
    if (!hasActive) return;
    const timer = setInterval(() => setRefreshKey((key) => key + 1), POLL_MS);
    return () => clearInterval(timer);
  }, [hasActive]);

  async function run(action: () => Promise<unknown>) {
    setActionError(null);
    try {
      await action();
      setRefreshKey((key) => key + 1);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <main className="page" data-testid="ComicsPage-main">
      <div className="spread">
        <h1 className="title">웹툰</h1>
        <button
          type="button"
          className="button secondary"
          disabled={hasActive}
          onClick={() => run(api.createComic)}
          data-testid="ComicsPage-createButton"
        >
          지금 한 편 그리기
        </button>
      </div>
      <Link to="/characters" className="chip" data-testid="ComicsPage-charactersLink">
        등장인물 관리 · 새 캐릭터 만들기
      </Link>
      <p className="muted" style={{ margin: 0 }}>
        월·수·금 새벽 3시에 곧 복습할 표현으로 새 에피소드가 그려져요.
      </p>
      {error && <p className="error">{error.message}</p>}
      {actionError && <p className="error">{actionError}</p>}
      {comics?.length === 0 && <p className="muted">아직 에피소드가 없어요.</p>}

      {comics?.map((comic) => (
        <div key={comic.id} className="card row" data-testid={`ComicsPage-item-${comic.id}`}>
          {comic.cover_url ? (
            <img src={comic.cover_url} alt="" className="comic-cover" />
          ) : (
            <div className="comic-cover comic-placeholder" />
          )}
          <div className="stack" style={{ gap: 4, flex: 1, minWidth: 0 }}>
            <Link
              to={`/comics/${comic.id}`}
              className="hand"
              style={{ fontSize: 22, lineHeight: 1.2, textDecoration: "none" }}
              data-testid={`ComicsPage-link-${comic.id}`}
            >
              {comic.title_ko || "새 에피소드"}
            </Link>
            <span className="muted">
              {new Date(comic.created_at).toLocaleDateString("ko-KR")} ·{" "}
              {STATUS_LABELS[comic.status]}
              {isActive(comic) && ` ${comic.panels_done}/${comic.panel_count}`}
              {comic.status === "done" && !comic.is_read && " · 새 에피소드"}
            </span>
            {comic.status === "failed" && (
              <>
                <span className="error">{comic.error}</span>
                <button
                  type="button"
                  className="button secondary"
                  onClick={() => run(() => api.retryComic(comic.id))}
                  data-testid={`ComicsPage-retryButton-${comic.id}`}
                >
                  이어서 그리기
                </button>
              </>
            )}
          </div>
        </div>
      ))}
    </main>
  );
}
