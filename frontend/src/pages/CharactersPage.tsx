import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { api, type CharacterSummary } from "../api";
import { Icon } from "../components/Icon";
import { useApi } from "../lib/useApi";

const STATUS_LABELS: Record<CharacterSummary["status"], string> = {
  draft: "초안",
  active: "웹툰 등장 중",
  resting: "쉬는 중",
};

export function CharactersPage() {
  const navigate = useNavigate();
  const { data: characters, error } = useApi(api.listCharacters, []);
  const [name, setName] = useState("");
  const [appearance, setAppearance] = useState("");
  const [isDrawing, setIsDrawing] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  async function handleCreate(event: FormEvent) {
    event.preventDefault();
    setIsDrawing(true);
    setCreateError(null);
    try {
      const created = await api.createCharacter(name.trim(), appearance.trim());
      navigate(`/characters/${created.id}`);
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : String(err));
      setIsDrawing(false);
    }
  }

  return (
    <main className="page" data-testid="CharactersPage-main">
      <div className="row" style={{ gap: 4 }}>
        <Link
          to="/comics"
          className="icon-button"
          aria-label="웹툰으로"
          data-testid="CharactersPage-backLink"
        >
          <Icon name="back" />
        </Link>
        <h1 className="title">캐릭터</h1>
      </div>
      <p className="muted" style={{ margin: 0 }}>
        확정한 캐릭터가 웹툰에 등장해요 (한 편에 최대 4명).
      </p>

      {error && <p className="error">{error.message}</p>}
      <div className="character-grid">
        {characters?.map((character) => (
          <Link
            key={character.id}
            to={`/characters/${character.id}`}
            className="card card-link character-card"
            data-testid={`CharactersPage-item-${character.id}`}
          >
            {character.image_url ? (
              <img src={character.image_url} alt="" />
            ) : (
              <div className="character-empty">첫 웹툰 때 그려져요</div>
            )}
            <strong className="hand" style={{ fontSize: 22 }}>
              {character.name}
            </strong>
            <span className={`tag ${character.status === "active" ? "tag-similar" : "tag-sense"}`}>
              {STATUS_LABELS[character.status]}
            </span>
          </Link>
        ))}
      </div>

      <form className="card stack" onSubmit={handleCreate} data-testid="CharactersPage-createForm">
        <span className="eyebrow">새 캐릭터 만들기</span>
        <label className="stack" style={{ gap: 6 }}>
          <span className="muted">이름</span>
          <input
            className="input"
            value={name}
            maxLength={30}
            onChange={(e) => setName(e.target.value)}
            placeholder="예: Sora"
            data-testid="CharactersPage-nameInput"
          />
        </label>
        <label className="stack" style={{ gap: 6 }}>
          <span className="muted">외모 · 성격 (한국어도 괜찮아요)</span>
          <textarea
            className="input"
            value={appearance}
            maxLength={500}
            onChange={(e) => setAppearance(e.target.value)}
            placeholder="예: 미나의 직장 동료, 20대 후반, 긴 웨이브 빨간 머리, 늘 커피를 들고 다니는 수다쟁이"
            data-testid="CharactersPage-appearanceInput"
          />
        </label>
        <button
          type="submit"
          className="button"
          disabled={isDrawing || !name.trim() || !appearance.trim()}
          data-testid="CharactersPage-createButton"
        >
          {isDrawing ? "그리는 중… (최대 1분)" : "그려보기"}
        </button>
        {createError && <p className="error">{createError}</p>}
      </form>
    </main>
  );
}
