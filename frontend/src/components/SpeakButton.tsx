import { useState } from "react";

import { playTts } from "../lib/speech";
import { Icon } from "./Icon";

interface SpeakButtonProps {
  text: string;
  label: string;
  testId: string;
}

/** Icon-only play button using the learner's saved accent/speed. */
export function SpeakButton({ text, label, testId }: SpeakButtonProps) {
  const [error, setError] = useState<string | null>(null);

  async function handleClick() {
    setError(null);
    try {
      await playTts(text);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <>
      <button
        type="button"
        className="icon-button"
        aria-label={label}
        title={error ?? label}
        onClick={handleClick}
        data-testid={testId}
        style={error ? { color: "var(--tangerine-dark)" } : undefined}
      >
        <Icon name="speaker" size={20} />
      </button>
      {error && (
        <span className="sr-only" role="alert">
          {error}
        </span>
      )}
    </>
  );
}
