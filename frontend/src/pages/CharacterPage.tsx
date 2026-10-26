import { useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";

import { api, type CharacterDetail } from "../api";
import { Icon } from "../components/Icon";
import { useApi } from "../lib/useApi";

export function CharacterPage() {
  const characterId = Number(useParams().characterId);
  const { data: loaded, error } = useApi(() => api.getCharacter(characterId), [characterId]);
  const [updated, setUpdated] = useState<CharacterDetail | null>(null);
  const [selectedNo, setSelectedNo] = useState<number | null>(null);
  const [instruction, setInstruction] = useState("");
  const [busy, setBusy] = useState<"revise" | "finalize" | "status" | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const character = updated ?? loaded;
  if (error) return <main className="page error">{error.message}</main>;
  if (!character) return <main className="page muted">불러오는 중…</main>;

  const latestNo = character.versions.at(-1)?.no ?? null;
  const shownNo = selectedNo ?? character.final_version ?? latestNo;
  const shown = character.versions.find((v) => v.no === shownNo);

  async function run(kind: typeof busy, action: () => Promise<CharacterDetail>) {
    setBusy(kind);
    setActionError(null);
    try {
      const next = await action();
      setUpdated(next);
      return next;
    } catch (err) {
      setActionError(err instanceof Error ? err.message : String(err));
      return null;
    } finally {
      setBusy(null);
    }
  }

  async function handleRevise(event: FormEvent) {
    event.preventDefault();
    if (shownNo === null) return;
    const next = await run("revise", () =>
      api.reviseCharacter(characterId, shownNo, instruction.trim()),
    );
    if (next) {
      setInstruction("");
      setSelectedNo(next.versions.at(-1)?.no ?? null);
    }
  }

  const isFinalShown = shownNo !== null && shownNo === character.final_version;

  return (
    <main className="page" data-testid="CharacterPage-main">
      <div className="row" style={{ gap: 4 }}>
        <Link
          to="/characters"
          className="icon-button"
          aria-label="캐릭터 목록으로"
          data-testid="CharacterPage-backLink"
        >
          <Icon name="back" />
        </Link>
        <h1 className="title">{character.name}</h1>
      </div>
      <p className="muted" style={{ margin: 0 }}>
        {character.appearance}
      </p>

      {shown ? (
        <figure className="character-stage" data-testid="CharacterPage-stage">
          <img src={shown.image_url} alt={`${character.name} ${shown.no}번 버전`} />
          <figcaption>
            v{shown.no} · {shown.instruction}
            {isFinalShown && " · 확정"}
          </figcaption>
        </figure>
      ) : (
        <div className="character-empty" style={{ height: 240 }}>
          아직 그린 버전이 없어요 — 첫 웹툰 때 자동으로 그려져요
        </div>
      )}

      {character.versions.length > 1 && (
        <div className="version-strip" role="group" aria-label="버전 선택">
          {character.versions.map((version) => (
            <button
              key={version.no}
              type="button"
              aria-pressed={version.no === shownNo}
              onClick={() => setSelectedNo(version.no)}
              data-testid={`CharacterPage-version-${version.no}`}
            >
              <img src={version.image_url} alt={`v${version.no}`} />
              <span>v{version.no}</span>
            </button>
          ))}
        </div>
      )}

      {shown && (
        <form className="card stack" onSubmit={handleRevise} data-testid="CharacterPage-reviseForm">
          <label className="stack" style={{ gap: 6 }}>
            <span className="eyebrow">v{shown.no}에서 고치기</span>
            <textarea
              className="input"
              value={instruction}
              maxLength={300}
              onChange={(e) => setInstruction(e.target.value)}
              placeholder="예: 머리를 단발로, 안경 추가, 더 밝은 표정"
              data-testid="CharacterPage-instructionInput"
            />
          </label>
          <button
            type="submit"
            className="button secondary"
            disabled={busy !== null || !instruction.trim()}
            data-testid="CharacterPage-reviseButton"
          >
            {busy === "revise" ? "다시 그리는 중… (최대 1분)" : "수정해서 다시 그리기"}
          </button>
        </form>
      )}

      {shown && !isFinalShown && (
        <button
          type="button"
          className="button"
          disabled={busy !== null}
          onClick={() => run("finalize", () => api.finalizeCharacter(characterId, shown.no))}
          data-testid="CharacterPage-finalizeButton"
        >
          v{shown.no}로 확정하고 웹툰에 등장시키기
        </button>
      )}
      {character.final_version !== null && (
        <button
          type="button"
          className="button secondary"
          disabled={busy !== null}
          onClick={() =>
            run("status", () =>
              api.setCharacterStatus(
                characterId,
                character.status === "active" ? "resting" : "active",
              ),
            )
          }
          data-testid="CharacterPage-statusButton"
        >
          {character.status === "active" ? "웹툰에서 잠시 빼기" : "웹툰에 다시 등장시키기"}
        </button>
      )}
      {actionError && <p className="error">{actionError}</p>}
    </main>
  );
}
