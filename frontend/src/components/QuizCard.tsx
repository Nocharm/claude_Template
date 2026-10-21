import { useState, type FormEvent } from "react";

import type { CheckResult, Grade, QuizItem } from "../api";

interface QuizCardProps {
  item: QuizItem;
  onCheck: (answer: string) => Promise<CheckResult>;
  onGrade: (grade: Grade) => void;
}

const KIND_LABELS: Record<QuizItem["kind"], string> = {
  cloze: "빈칸 채우기",
  ko_to_en: "한→영 표현",
};

/** One question: answer → server check → learner picks how well they knew it. */
export function QuizCard({ item, onCheck, onGrade }: QuizCardProps) {
  const [answer, setAnswer] = useState("");
  const [result, setResult] = useState<CheckResult | null>(null);
  const [showHint, setShowHint] = useState(false);
  const [isChecking, setIsChecking] = useState(false);
  const [blankBefore, blankAfter] = item.prompt_en.split("____");

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (result || !answer.trim()) return;
    setIsChecking(true);
    try {
      setResult(await onCheck(answer));
    } finally {
      setIsChecking(false);
    }
  }

  return (
    <form className="stack" style={{ gap: 16 }} onSubmit={handleSubmit} data-testid="QuizCard-form">
      <div className="row" style={{ gap: 6 }}>
        <span className="tag tag-same_sentence">{KIND_LABELS[item.kind]}</span>
        {item.is_new && <span className="tag tag-similar">새 표현</span>}
        <span className="muted">DAY {item.day_no}</span>
      </div>

      <div className="quiz-sheet">
        <div style={{ color: "var(--ink-2)" }}>{item.prompt_ko}</div>
        {item.kind === "cloze" && (
          <div className="quiz-en">
            {blankBefore}
            <span className="blank">{result ? result.expected : " "}</span>
            {blankAfter}
          </div>
        )}
      </div>

      <label className="stack" style={{ gap: 6 }}>
        <span className="eyebrow">내 답</span>
        <input
          className="input"
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
          autoCapitalize="off"
          autoComplete="off"
          autoCorrect="off"
          spellCheck={false}
          readOnly={result !== null}
          placeholder={showHint ? `${item.hint}…` : "영어로 입력"}
          data-testid="QuizCard-answerInput"
        />
      </label>

      {result === null ? (
        <div className="button-row">
          <button
            type="button"
            className="button secondary"
            onClick={() => setShowHint(true)}
            disabled={showHint}
            data-testid="QuizCard-hintButton"
          >
            힌트
          </button>
          <button
            type="submit"
            className="button"
            disabled={isChecking || !answer.trim()}
            data-testid="QuizCard-checkButton"
          >
            확인
          </button>
        </div>
      ) : (
        <>
          <div
            role="status"
            className={`feedback ${result.is_correct ? "correct" : "wrong"}`}
            data-testid="QuizCard-feedback"
          >
            <strong>{result.is_correct ? "정답이에요!" : "아쉬워요"}</strong>
            <span className="muted">
              <b className="hand" style={{ fontSize: 19, color: "var(--ink)" }}>
                {result.expected}
              </b>{" "}
              — {result.meaning_ko}
            </span>
          </div>
          {result.is_correct ? (
            <div className="button-row">
              <button
                type="button"
                className="button secondary"
                onClick={() => onGrade("hard")}
                data-testid="QuizCard-hardButton"
              >
                헷갈렸어요
              </button>
              <button
                type="button"
                className="button"
                onClick={() => onGrade("good")}
                data-testid="QuizCard-goodButton"
              >
                다음 문제
              </button>
            </div>
          ) : (
            <button
              type="button"
              className="button"
              onClick={() => onGrade("again")}
              data-testid="QuizCard-againButton"
            >
              다시 나오게 하고 다음으로
            </button>
          )}
        </>
      )}
    </form>
  );
}
