import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api } from "../api";
import { ComicPanel } from "../components/ComicPanel";
import { Icon } from "../components/Icon";
import { playTts } from "../lib/speech";
import { useApi } from "../lib/useApi";

export function ComicPage() {
  const comicId = Number(useParams().comicId);
  const { data: comic, error } = useApi(() => api.getComic(comicId), [comicId]);
  const [isKoreanShown, setIsKoreanShown] = useState(false);
  const [readXp, setReadXp] = useState<number | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  if (error) return <main className="page error">{error.message}</main>;
  if (!comic) return <main className="page muted">불러오는 중…</main>;

  async function handleSpeak(text: string) {
    try {
      setActionError(null);
      await playTts(text);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : String(err));
    }
  }

  async function handleFinish() {
    try {
      setReadXp((await api.markComicRead(comicId)).xp_gained);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <main className="page" data-testid="ComicPage-main">
      <div className="spread">
        <Link
          to="/comics"
          className="icon-button"
          aria-label="목록으로"
          data-testid="ComicPage-backLink"
        >
          <Icon name="back" />
        </Link>
        <div className="segmented" role="group" aria-label="번역 표시">
          <button
            type="button"
            aria-pressed={!isKoreanShown}
            onClick={() => setIsKoreanShown(false)}
            data-testid="ComicPage-englishOnlyButton"
          >
            영어만
          </button>
          <button
            type="button"
            aria-pressed={isKoreanShown}
            onClick={() => setIsKoreanShown(true)}
            data-testid="ComicPage-koreanButton"
          >
            해석 같이
          </button>
        </div>
        <span style={{ width: 44 }} />
      </div>

      <h1 className="title">{comic.title_ko || "새 에피소드"}</h1>
      <div className="wrap">
        {comic.expressions.map((expression) => (
          <Link
            key={expression.id}
            to={`/expressions/${expression.id}`}
            className="tag tag-similar"
            style={{ fontSize: 12, padding: "4px 8px", textDecoration: "none" }}
            data-testid={`ComicPage-expression-${expression.id}`}
          >
            {expression.text}
          </Link>
        ))}
      </div>
      <p className="muted" style={{ margin: 0 }}>
        말풍선을 누르면 읽어 줘요
      </p>

      <div className="stack" style={{ gap: 14 }}>
        {comic.panels.map((panel) => (
          <ComicPanel
            key={panel.no}
            no={panel.no}
            imageUrl={panel.image_url}
            bubbles={panel.bubbles}
            isKoreanShown={isKoreanShown}
            onSpeak={handleSpeak}
          />
        ))}
      </div>

      {actionError && <p className="error">{actionError}</p>}
      {comic.status === "done" &&
        (readXp === null && !comic.is_read ? (
          <button
            type="button"
            className="button"
            onClick={handleFinish}
            data-testid="ComicPage-finishButton"
          >
            다 읽었어요 (+10 XP)
          </button>
        ) : (
          <p className="muted" style={{ textAlign: "center" }}>
            {readXp ? `+${readXp} XP 받았어요!` : "다 읽은 에피소드예요"}
          </p>
        ))}
    </main>
  );
}
