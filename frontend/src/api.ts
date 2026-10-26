// Typed client for the FastAPI backend (shapes mirror backend/app/main.py response models).

export interface Book {
  id: number;
  title: string;
  page_count: number | null;
  status: "queued" | "classifying" | "extracting" | "linking" | "done" | "failed";
  progress_done: number;
  progress_total: number;
  error: string | null;
}

export interface DaySummary {
  id: number;
  day_no: number;
  title: string;
  expression_count: number;
}

export interface ExpressionRef {
  id: number;
  text: string;
  highlight: string;
  meaning_ko: string;
}

export interface Sentence {
  id: number;
  no: number;
  text_en: string;
  text_ko: string;
  expressions: ExpressionRef[];
}

export interface DayDetail {
  id: number;
  book_id: number;
  day_no: number;
  title: string;
  passage_en: string;
  prev_day_id: number | null;
  next_day_id: number | null;
  sentences: Sentence[];
}

export type RelationType = "similar" | "sense" | "contrast" | "same_sentence";

export interface Related {
  id: number;
  text: string;
  meaning_ko: string;
  day_no: number;
  type: RelationType;
  note: string;
}

export interface ExpressionDetail {
  id: number;
  text: string;
  meaning_ko: string;
  explanation_ko: string;
  origin: "reading_point" | "tip_box";
  day_id: number;
  day_no: number;
  day_title: string;
  sentence: { no: number; text_en: string; text_ko: string } | null;
  examples: { text_en: string; text_ko: string; origin: string }[];
  related: Related[];
}

export interface Daily {
  date: string;
  answered: number;
  goal: number;
  goal_met: boolean;
  xp_today: number;
}

export interface QuizItem {
  expression_id: number;
  day_no: number;
  kind: "cloze" | "ko_to_en";
  prompt_ko: string;
  prompt_en: string;
  hint: string;
  is_new: boolean;
}

export interface CheckResult {
  is_correct: boolean;
  expected: string;
  meaning_ko: string;
}

export type Grade = "again" | "hard" | "good";

export interface GradeResult {
  xp_gained: number;
  next_due: string;
  goal_just_met: boolean;
  today: Daily;
}

export type DayStatus = "met" | "partial" | "rest" | "none" | "future";

export interface Progress {
  today: Daily;
  streak_days: number;
  level: number;
  level_name: string;
  xp_total: number;
  xp_into_level: number;
  xp_for_next: number;
  mastered: number;
  month: string;
  calendar: { date: string; status: DayStatus }[];
}

export type Scenario = "work" | "travel" | "daily" | "romance";

export interface Application {
  id: number;
  scenario: Scenario;
  scenario_label: string;
  text_en: string;
  text_ko: string;
  highlight: string;
}

export interface Feedback {
  uses_expression: boolean;
  is_natural: boolean;
  corrected_en: string;
  explanation_ko: string;
  xp_gained: number;
}

export interface ComicSummary {
  id: number;
  created_at: string;
  status: "queued" | "writing" | "drawing" | "done" | "failed";
  title_ko: string;
  panels_done: number;
  panel_count: number;
  error: string | null;
  cover_url: string | null;
  is_read: boolean;
}

export interface ComicBubble {
  speaker: string; // cast id like "c3", or "narration"
  text_en: string;
  text_ko: string;
  highlight: string;
}

export interface ComicDetail extends ComicSummary {
  expressions: { id: number; text: string; meaning_ko: string }[];
  panels: { no: number; image_url: string | null; bubbles: ComicBubble[] }[];
}

export interface CharacterSummary {
  id: number;
  name: string;
  appearance: string;
  status: "draft" | "active" | "resting";
  final_version: number | null;
  image_url: string | null;
  version_count: number;
}

export interface CharacterDetail extends CharacterSummary {
  versions: { no: number; instruction: string; image_url: string }[];
}

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly path: string,
    detail: string,
  ) {
    super(`${status} ${path}: ${detail}`);
  }
}

function postJson(body: unknown): RequestInit {
  return {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null);
    const detail =
      body && typeof body === "object" && "detail" in body
        ? String(body.detail)
        : response.statusText;
    throw new ApiError(response.status, path, detail);
  }
  return (await response.json()) as T;
}

export const api = {
  listBooks: () => request<Book[]>("/api/books"),
  getBook: (id: number) => request<Book>(`/api/books/${id}`),
  uploadBook: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<Book>("/api/books", { method: "POST", body: form });
  },
  retryBook: (id: number) => request<Book>(`/api/books/${id}/retry`, { method: "POST" }),
  listDays: (bookId: number) => request<DaySummary[]>(`/api/books/${bookId}/days`),
  getDay: (id: number) => request<DayDetail>(`/api/days/${id}`),
  getExpression: (id: number) => request<ExpressionDetail>(`/api/expressions/${id}`),
  getQueue: () => request<{ items: QuizItem[]; today: Daily }>("/api/study/queue"),
  checkAnswer: (expressionId: number, answer: string) =>
    request<CheckResult>(`/api/study/${expressionId}/check`, postJson({ answer })),
  gradeCard: (expressionId: number, grade: Grade) =>
    request<GradeResult>(`/api/study/${expressionId}/grade`, postJson({ grade })),
  getProgress: (month?: string) =>
    request<Progress>(`/api/study/progress${month ? `?month=${month}` : ""}`),
  listApplications: (expressionId: number) =>
    request<Application[]>(`/api/expressions/${expressionId}/applications`),
  createApplications: (expressionId: number, scenario: Scenario) =>
    request<Application[]>(`/api/expressions/${expressionId}/applications`, postJson({ scenario })),
  createFeedback: (expressionId: number, sentence: string) =>
    request<Feedback>(`/api/expressions/${expressionId}/feedback`, postJson({ sentence })),
  listComics: () => request<ComicSummary[]>("/api/comics"),
  createComic: () => request<ComicSummary>("/api/comics", { method: "POST" }),
  retryComic: (id: number) => request<ComicSummary>(`/api/comics/${id}/retry`, { method: "POST" }),
  getComic: (id: number) => request<ComicDetail>(`/api/comics/${id}`),
  listCharacters: () => request<CharacterSummary[]>("/api/characters"),
  getCharacter: (id: number) => request<CharacterDetail>(`/api/characters/${id}`),
  createCharacter: (name: string, appearance: string) =>
    request<CharacterDetail>("/api/characters", postJson({ name, appearance })),
  reviseCharacter: (id: number, baseVersion: number, instruction: string) =>
    request<CharacterDetail>(
      `/api/characters/${id}/versions`,
      postJson({ base_version: baseVersion, instruction }),
    ),
  finalizeCharacter: (id: number, version: number) =>
    request<CharacterDetail>(`/api/characters/${id}/finalize`, postJson({ version })),
  setCharacterStatus: (id: number, status: "active" | "resting") =>
    request<CharacterDetail>(`/api/characters/${id}/status`, postJson({ status })),
  markComicRead: (id: number) =>
    request<{ xp_gained: number }>(`/api/comics/${id}/read`, { method: "POST" }),
};

export const RELATION_LABELS: Record<RelationType, string> = {
  similar: "유사",
  sense: "다른 쓰임",
  contrast: "대조",
  same_sentence: "같은 문장",
};
