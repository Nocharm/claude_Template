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
