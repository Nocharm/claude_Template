import { useState } from "react";

import { playTts } from "../lib/speech";
import { getVoicePrefs, setVoicePrefs, type Accent } from "../lib/storage";
import { Icon } from "./Icon";

const ACCENTS: { accent: Accent; label: string }[] = [
  { accent: "us", label: "미국" },
  { accent: "uk", label: "영국" },
  { accent: "au", label: "호주" },
  { accent: "in", label: "인도" },
];

interface SpeakControlsProps {
  text: string;
}

/** Accent chips: tapping one plays the text in that accent and remembers it as the default. */
export function SpeakControls({ text }: SpeakControlsProps) {
  const [prefs, setPrefs] = useState(getVoicePrefs);
  const [error, setError] = useState<string | null>(null);

  async function handlePlay(accent: Accent, isSlow: boolean) {
    const next = { accent, isSlow };
    setPrefs(next);
    setVoicePrefs(next);
    setError(null);
    try {
      await playTts(text, accent, isSlow);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <div className="stack" style={{ gap: 6 }}>
      <div className="wrap" role="group" aria-label="억양별 듣기" data-testid="SpeakControls-group">
        {ACCENTS.map(({ accent, label }) => (
          <button
            key={accent}
            type="button"
            className={`voice-chip${prefs.accent === accent ? " active" : ""}`}
            aria-pressed={prefs.accent === accent}
            onClick={() => handlePlay(accent, prefs.isSlow)}
            data-testid={`SpeakControls-accent-${accent}`}
          >
            {prefs.accent === accent && <Icon name="speaker" size={16} />}
            {label}
          </button>
        ))}
        <button
          type="button"
          className={`voice-chip${prefs.isSlow ? " active" : ""}`}
          aria-pressed={prefs.isSlow}
          onClick={() => handlePlay(prefs.accent, !prefs.isSlow)}
          data-testid="SpeakControls-slowToggle"
        >
          0.75×
        </button>
      </div>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
