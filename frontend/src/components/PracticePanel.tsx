import { useState, type FormEvent } from "react";

import { api, type Application, type Feedback, type Scenario } from "../api";
import { useApi } from "../lib/useApi";
import { Highlighted } from "./Highlighted";

const SCENARIO_BUTTONS: { scenario: Scenario; label: string }[] = [
  { scenario: "work", label: "회사" },
  { scenario: "travel", label: "여행" },
  { scenario: "daily", label: "일상" },
  { scenario: "romance", label: "연애" },
];

interface PracticePanelProps {
  expressionId: number;
}

/** AI-made situational examples (cached server-side) and feedback on the learner's own sentence. */
export function PracticePanel({ expressionId }: PracticePanelProps) {
  const { data: saved } = useApi(() => api.listApplications(expressionId), [expressionId]);
  const [created, setCreated] = useState<Application[] | null>(null);
  const [pending, setPending] = useState<Scenario | null>(null);
  const [sentence, setSentence] = useState("");
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [isReviewing, setIsReviewing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const applications = created ?? saved ?? [];

  async function handleApply(scenario: Scenario) {
    setPending(scenario);
    setError(null);
    try {
      setCreated(await api.createApplications(expressionId, scenario));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setPending(null);
    }
  }

  async function handleReview(event: FormEvent) {
    event.preventDefault();
    setIsReviewing(true);
    setError(null);
    try {
      setFeedback(await api.createFeedback(expressionId, sentence.trim()));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsReviewing(false);
    }
  }

  return (
    <section
      className="card stack"
      style={{ background: "#f1f8f3", borderColor: "var(--marker)" }}
      data-testid="PracticePanel-section"
    >
      <span className="eyebrow" style={{ color: "var(--green-dark)" }}>
        응용 — 상황을 골라 예문 만들기
      </span>
      <div className="wrap">
        {SCENARIO_BUTTONS.map(({ scenario, label }) => (
          <button
            key={scenario}
            type="button"
            className="chip"
            disabled={pending !== null}
            onClick={() => handleApply(scenario)}
            data-testid={`PracticePanel-scenario-${scenario}`}
          >
            {pending === scenario ? "만드는 중…" : label}
          </button>
        ))}
      </div>

      {applications.map((application) => (
        <div
          key={application.id}
          style={{ borderTop: "1px solid var(--marker)", paddingTop: 10 }}
          data-testid={`PracticePanel-application-${application.id}`}
        >
          <span className="tag tag-similar">{application.scenario_label}</span>
          <div style={{ marginTop: 4 }}>
            <Highlighted
              text={application.text_en}
              marks={[{ id: application.id, highlight: application.highlight }]}
            />
          </div>
          <div className="muted">{application.text_ko}</div>
        </div>
      ))}

      <form
        className="stack"
        onSubmit={handleReview}
        style={{ borderTop: "1px solid var(--marker)", paddingTop: 12 }}
      >
        <label className="stack" style={{ gap: 6 }}>
          <span className="eyebrow" style={{ color: "var(--green-dark)" }}>
            내 문장 첨삭 (+15 XP)
          </span>
          <textarea
            className="input"
            value={sentence}
            maxLength={300}
            onChange={(e) => setSentence(e.target.value)}
            placeholder="이 표현으로 문장을 써 보세요"
            data-testid="PracticePanel-sentenceInput"
          />
        </label>
        <button
          type="submit"
          className="button"
          disabled={isReviewing || !sentence.trim()}
          data-testid="PracticePanel-reviewButton"
        >
          {isReviewing ? "보는 중…" : "첨삭 받기"}
        </button>
      </form>

      {feedback && (
        <div
          role="status"
          className={`feedback ${feedback.is_natural && feedback.uses_expression ? "correct" : "wrong"}`}
          data-testid="PracticePanel-feedback"
        >
          {feedback.corrected_en !== sentence.trim() && (
            <span className="hand" style={{ fontSize: 20 }}>
              {feedback.corrected_en}
            </span>
          )}
          <span>{feedback.explanation_ko}</span>
          {feedback.xp_gained > 0 && (
            <span className="number" style={{ color: "var(--green)" }}>
              +{feedback.xp_gained} XP
            </span>
          )}
        </div>
      )}
      {error && <p className="error">{error}</p>}
    </section>
  );
}
