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

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly path: string,
    detail: string,
  ) {
    super(`${status} ${path}: ${detail}`);
  }
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
};

export const RELATION_LABELS: Record<RelationType, string> = {
  similar: "유사",
  sense: "다른 쓰임",
  contrast: "대조",
  same_sentence: "같은 문장",
};
