// Per-device convenience state; storage can be unavailable (private mode), so never required.

const LAST_DAY_KEY = "lastDayId";

export function getLastDayId(): number | null {
  try {
    const value = localStorage.getItem(LAST_DAY_KEY);
    return value ? Number(value) : null;
  } catch {
    return null;
  }
}

export function setLastDayId(dayId: number): void {
  try {
    localStorage.setItem(LAST_DAY_KEY, String(dayId));
  } catch {
    // Storage blocked: "continue reading" just won't be remembered on this device.
  }
}

const VOICE_KEY = "voicePrefs";

export type Accent = "us" | "uk" | "au" | "in";

export interface VoicePrefs {
  accent: Accent;
  isSlow: boolean;
}

const DEFAULT_VOICE: VoicePrefs = { accent: "us", isSlow: false };

export function getVoicePrefs(): VoicePrefs {
  try {
    const value = localStorage.getItem(VOICE_KEY);
    return value
      ? { ...DEFAULT_VOICE, ...(JSON.parse(value) as Partial<VoicePrefs>) }
      : DEFAULT_VOICE;
  } catch {
    return DEFAULT_VOICE;
  }
}

export function setVoicePrefs(prefs: VoicePrefs): void {
  try {
    localStorage.setItem(VOICE_KEY, JSON.stringify(prefs));
  } catch {
    // Storage blocked: the chosen accent just resets next visit.
  }
}
