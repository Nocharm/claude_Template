import { Link, useNavigate, useParams } from "react-router-dom";

import { api, RELATION_LABELS } from "../api";
import { Icon } from "../components/Icon";
import { PracticePanel } from "../components/PracticePanel";
import { SpeakButton } from "../components/SpeakButton";
import { SpeakControls } from "../components/SpeakControls";
import { useApi } from "../lib/useApi";

function buildYouglishUrl(text: string): string {
  // Placeholders like "~" and sentence punctuation break the phrase search.
  const phrase = text.replace(/[~.?!]/g, "").trim();
  return `https://youglish.com/pronounce/${encodeURIComponent(phrase)}/english`;
}

export function ExpressionPage() {
  const expressionId = Number(useParams().expressionId);
  const navigate = useNavigate();
  const { data: expression, error } = useApi(() => api.getExpression(expressionId), [expressionId]);

  if (error) return <main className="page error">{error.message}</main>;
  if (!expression) return <main className="page muted">불러오는 중…</main>;

  return (
    <main className="page" data-testid="ExpressionPage-main">
      <div className="spread">
        <button
          type="button"
          className="icon-button"
          aria-label="뒤로"
          onClick={() => navigate(-1)}
          data-testid="ExpressionPage-backButton"
        >
          <Icon name="back" />
        </button>
        <Link
          to={`/days/${expression.day_id}`}
          className="muted"
          data-testid="ExpressionPage-dayLink"
        >
          DAY {expression.day_no}
          {expression.sentence && ` · 문장 ${expression.sentence.no}`}
        </Link>
        <Link
          to={`/map?expression=${expression.id}`}
          className="eyebrow"
          style={{ color: "var(--green)", minHeight: 44, display: "flex", alignItems: "center" }}
          data-testid="ExpressionPage-mapLink"
        >
          맵에서 보기
        </Link>
      </div>

      <header className="stack" style={{ gap: 4 }}>
        <h1 className="hand" style={{ margin: 0, fontSize: 44, lineHeight: 1.1, fontWeight: 400 }}>
          <span className="marker">{expression.text}</span>
        </h1>
        <div style={{ fontSize: 17, fontWeight: 700 }}>{expression.meaning_ko}</div>
      </header>

      <SpeakControls text={expression.text} />

      {(expression.explanation_ko || expression.examples.length > 0) && (
        <section className="card stack" data-testid="ExpressionPage-explanation">
          {expression.explanation_ko && <p style={{ margin: 0 }}>{expression.explanation_ko}</p>}
          {expression.examples.map((example, i) => (
            <div
              key={i}
              className="spread"
              style={{ borderTop: "1px solid #eceae4", paddingTop: 10, alignItems: "flex-start" }}
            >
              <div>
                <div>{example.text_en}</div>
                <div className="muted">{example.text_ko}</div>
              </div>
              <SpeakButton
                text={example.text_en}
                label="예문 듣기"
                testId={`ExpressionPage-exampleSpeak-${i}`}
              />
            </div>
          ))}
        </section>
      )}

      {expression.sentence && (
        <section className="card stack" style={{ background: "var(--butter)", border: 0 }}>
          <div className="spread">
            <span className="eyebrow">책 속 문장</span>
            <SpeakButton
              text={expression.sentence.text_en}
              label="책 속 문장 듣기"
              testId="ExpressionPage-sentenceSpeak"
            />
          </div>
          <span className="hand" style={{ fontSize: 21, lineHeight: 1.35 }}>
            {expression.sentence.text_en}
          </span>
          <span className="muted">{expression.sentence.text_ko}</span>
        </section>
      )}

      {expression.related.length > 0 && (
        <section className="stack" data-testid="ExpressionPage-related">
          <span className="eyebrow">연결된 표현</span>
          <div className="wrap">
            {expression.related.map((related) => (
              <Link
                key={`${related.type}-${related.id}`}
                to={`/expressions/${related.id}`}
                className="chip"
                data-testid={`ExpressionPage-related-${related.id}`}
              >
                <span className={`tag tag-${related.type}`}>{RELATION_LABELS[related.type]}</span>
                {related.type === "sense" ? related.meaning_ko : related.text}
              </Link>
            ))}
          </div>
        </section>
      )}

      <PracticePanel expressionId={expression.id} />

      <a
        href={buildYouglishUrl(expression.text)}
        target="_blank"
        rel="noreferrer"
        className="button secondary"
        data-testid="ExpressionPage-youglishLink"
      >
        <Icon name="play" size={18} />
        실제 영상에서 듣기
      </a>
    </main>
  );
}
