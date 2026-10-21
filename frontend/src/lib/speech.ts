// Plays server-cached Azure TTS; one shared element so a new tap stops the previous clip.

import { getVoicePrefs, type Accent } from "./storage";

let player: HTMLAudioElement | null = null;

export function buildTtsUrl(text: string, accent: Accent, isSlow: boolean): string {
  const params = new URLSearchParams({ text, accent, slow: String(isSlow) });
  return `/api/tts?${params}`;
}

/** Strip study placeholders ("have always been ~") that shouldn't be read aloud. */
export function cleanForSpeech(text: string): string {
  return text.replace(/~/g, "").replace(/\s+/g, " ").trim();
}

/** Must be called from a tap handler: iOS only allows audio started by a user gesture. */
export async function playTts(text: string, accent?: Accent, isSlow?: boolean): Promise<void> {
  const prefs = getVoicePrefs();
  player?.pause();
  player = new Audio(
    buildTtsUrl(cleanForSpeech(text), accent ?? prefs.accent, isSlow ?? prefs.isSlow),
  );
  try {
    await player.play();
  } catch (err) {
    // A newer tap paused this clip on purpose; that's not a failure.
    if (err instanceof DOMException && err.name === "AbortError") return;
    throw new Error(`음성을 재생하지 못했어요 (Azure 설정을 확인하세요): ${String(err)}`, {
      cause: err,
    });
  }
}
