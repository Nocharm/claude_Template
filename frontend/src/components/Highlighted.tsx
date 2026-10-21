import { Link } from "react-router-dom";

import { splitHighlights, type Mark } from "../lib/highlight";

interface HighlightedProps {
  text: string;
  marks: Mark[];
  /** Render marks as links to the expression page (off inside buttons, where links can't nest). */
  isLinked?: boolean;
}

export function Highlighted({ text, marks, isLinked = false }: HighlightedProps) {
  return (
    <>
      {splitHighlights(text, marks).map((segment, i) => {
        if (segment.markId === null) return <span key={i}>{segment.text}</span>;
        return isLinked ? (
          <Link
            key={i}
            to={`/expressions/${segment.markId}`}
            className="marker"
            data-testid={`Highlighted-mark-${segment.markId}`}
          >
            {segment.text}
          </Link>
        ) : (
          <span key={i} className="marker">
            {segment.text}
          </span>
        );
      })}
    </>
  );
}
