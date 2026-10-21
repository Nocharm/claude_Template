import type { ComicBubble } from "../api";
import { Highlighted } from "./Highlighted";

interface ComicPanelProps {
  no: number;
  imageUrl: string | null;
  bubbles: ComicBubble[];
  isKoreanShown: boolean;
  onSpeak: (text: string) => void;
}

/** Text-free Gemini art with HTML speech bubbles on top (tap a bubble to hear it). */
export function ComicPanel({ no, imageUrl, bubbles, isKoreanShown, onSpeak }: ComicPanelProps) {
  return (
    <figure className="comic-panel" data-testid={`ComicPanel-panel-${no}`}>
      {imageUrl ? (
        <img src={imageUrl} alt={`${no}컷`} loading="lazy" />
      ) : (
        <div className="comic-placeholder">그리는 중…</div>
      )}
      <div className="comic-bubbles">
        {bubbles.map((bubble, i) => (
          <button
            key={i}
            type="button"
            className={`comic-bubble ${bubble.speaker}`}
            onClick={() => onSpeak(bubble.text_en)}
            aria-label={`${bubble.text_en} 듣기`}
            data-testid={`ComicPanel-bubble-${no}-${i}`}
          >
            <Highlighted text={bubble.text_en} marks={[{ id: i, highlight: bubble.highlight }]} />
            {isKoreanShown && <span className="comic-ko">{bubble.text_ko}</span>}
          </button>
        ))}
      </div>
      <figcaption className="comic-no">{no} / 10</figcaption>
    </figure>
  );
}
