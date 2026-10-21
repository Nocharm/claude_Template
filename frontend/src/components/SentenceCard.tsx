import { useState } from "react";
import { Link } from "react-router-dom";

import type { Sentence } from "../api";
import { Highlighted } from "./Highlighted";

interface SentenceCardProps {
  sentence: Sentence;
}

/** Front: English with markers. Tap to flip → Korean translation; expression links below. */
export function SentenceCard({ sentence }: SentenceCardProps) {
  const [isFlipped, setIsFlipped] = useState(false);

  return (
    <div className="stack">
      <button
        type="button"
        className="flip"
        aria-pressed={isFlipped}
        aria-label={`문장 ${sentence.no} 카드 뒤집기`}
        onClick={() => setIsFlipped((value) => !value)}
        data-testid={`SentenceCard-flip-${sentence.no}`}
      >
        <div className="flip-inner">
          <div className="flip-face" aria-hidden={isFlipped}>
            <span className="eyebrow">문장 {sentence.no}</span>
            <span className="flip-en">
              <Highlighted text={sentence.text_en} marks={sentence.expressions} />
            </span>
            <span className="muted">탭해서 뒤집기</span>
          </div>
          <div className="flip-face flip-back" aria-hidden={!isFlipped}>
            <span className="eyebrow">해석</span>
            <span className="flip-ko">{sentence.text_ko}</span>
          </div>
        </div>
      </button>
      {sentence.expressions.length > 0 && (
        <div className="wrap">
          {sentence.expressions.map((expression) => (
            <Link
              key={expression.id}
              to={`/expressions/${expression.id}`}
              className="chip"
              data-testid={`SentenceCard-expression-${expression.id}`}
            >
              <span className="hand" style={{ fontSize: 19 }}>
                {expression.text}
              </span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
