import axios from "axios";
import type {
  DetectionResult,
  PlagiarismResult,
  HumanizationResult,
  AnalysisOptions,
  HistoryItem,
  PaginatedResponse,
} from "@/types/analysis";
import type {
  ReadabilityResult,
  ToneResult,
  GrammarResult,
  TextStatistics,
  WritingSuggestionsResult,
  CitationResult,
  ComparisonResult,
  FullAnalyticsResult,
} from "@/types/analytics";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "/api/v1",
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 120000,
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const message =
      error.response?.data?.detail ||
      error.response?.data?.message ||
      error.message ||
      "An unexpected error occurred";
    return Promise.reject(new Error(message));
  }
);

export async function analyzeText(
  text: string,
  mode: string = "deep",
  options?: AnalysisOptions
): Promise<DetectionResult> {
  const { data } = await api.post<DetectionResult>("/detect", {
    text,
    mode,
    ...options,
  });
  return data;
}

export async function analyzePlagiarism(
  text: string,
  options?: AnalysisOptions
): Promise<PlagiarismResult> {
  const { data } = await api.post<PlagiarismResult>("/plagiarism", {
    text,
    ...options,
  });
  return data;
}

export async function humanizeText(
  text: string,
  style: string = "academic",
  options?: AnalysisOptions
): Promise<HumanizationResult> {
  const { data } = await api.post<HumanizationResult>("/humanize", {
    text,
    style,
    ...options,
  });
  return data;
}

export async function getHistory(
  page: number = 1,
  limit: number = 20
): Promise<PaginatedResponse<HistoryItem>> {
  const { data } = await api.get<PaginatedResponse<HistoryItem>>("/history", {
    params: { page, limit },
  });
  return data;
}

export async function getHealth(): Promise<{ status: string }> {
  const { data } = await api.get<{ status: string }>("/health");
  return data;
}

// --- Analytics endpoints ---

export async function analyzeReadability(text: string): Promise<ReadabilityResult> {
  const { data } = await api.post<ReadabilityResult>("/analytics/readability", { text });
  return data;
}

export async function analyzeTone(text: string): Promise<ToneResult> {
  const { data } = await api.post<ToneResult>("/analytics/tone", { text });
  return data;
}

export async function checkGrammar(text: string): Promise<GrammarResult> {
  const { data } = await api.post<GrammarResult>("/analytics/grammar", { text });
  return data;
}

export async function getStatistics(text: string): Promise<TextStatistics> {
  const { data } = await api.post<TextStatistics>("/analytics/statistics", { text });
  return data;
}

export async function getSuggestions(text: string): Promise<WritingSuggestionsResult> {
  const { data } = await api.post<WritingSuggestionsResult>("/analytics/suggestions", { text });
  return data;
}

export async function extractCitations(text: string): Promise<CitationResult> {
  const { data } = await api.post<CitationResult>("/analytics/citations", { text });
  return data;
}

export async function compareTexts(
  textA: string,
  textB: string
): Promise<ComparisonResult> {
  const { data } = await api.post<ComparisonResult>("/analytics/compare", {
    text_a: textA,
    text_b: textB,
  });
  return data;
}

export async function runFullAnalytics(text: string): Promise<FullAnalyticsResult> {
  const { data } = await api.post<FullAnalyticsResult>("/analytics/full", { text });
  return data;
}

// --- Export endpoints ---

export async function exportPdf(
  data: Record<string, unknown>,
  text: string
): Promise<Blob> {
  const response = await api.post(
    "/export/pdf",
    { data, text },
    { responseType: "blob" }
  );
  return response.data;
}

export async function exportJson(data: Record<string, unknown>): Promise<Blob> {
  const response = await api.post(
    "/export/json",
    { data },
    { responseType: "blob" }
  );
  return response.data;
}

export async function exportCsv(data: Record<string, unknown>): Promise<Blob> {
  const response = await api.post(
    "/export/csv",
    { data },
    { responseType: "blob" }
  );
  return response.data;
}

export async function getShareLink(
  data: Record<string, unknown>
): Promise<{ url: string }> {
  const { data: result } = await api.post<{ url: string }>("/export/share", {
    data,
  });
  return result;
}

// --- Paraphrase / Fact Check / SEO / Dashboard endpoints ---

import type {
  ParaphraseResult,
  FactCheckResult,
  SEOResult,
  DashboardStats,
  DashboardTrends,
  TopSignal,
} from "@/types/analytics";

export async function analyzeParaphrase(text: string): Promise<ParaphraseResult> {
  const { data } = await api.post<ParaphraseResult>("/analytics/paraphrase", { text });
  return data;
}

export async function checkFacts(text: string): Promise<FactCheckResult> {
  const { data } = await api.post<FactCheckResult>("/analytics/facts", { text });
  return data;
}

export async function analyzeSEO(text: string): Promise<SEOResult> {
  const { data } = await api.post<SEOResult>("/analytics/seo", { text });
  return data;
}

export async function getDashboardStats(): Promise<DashboardStats> {
  const { data } = await api.get<DashboardStats>("/dashboard/stats");
  return data;
}

export async function getDashboardTrends(): Promise<DashboardTrends> {
  const { data } = await api.get<DashboardTrends>("/dashboard/trends");
  return data;
}

export async function getTopSignals(limit: number = 10): Promise<TopSignal[]> {
  const { data } = await api.get<TopSignal[]>("/dashboard/top-signals", {
    params: { limit },
  });
  return data;
}

// --- Rewrite Detection ---

export interface RewriteDetectionResponse {
  isRewritten: boolean;
  naturalnessScore: number;
  confidence: number;
  residualPatterns: {
    id: string;
    pattern: string;
    description: string;
    severity: "high" | "medium" | "low";
    count: number;
  }[];
  explanation: string;
}

export async function detectRewrite(text: string): Promise<RewriteDetectionResponse> {
  const { data } = await api.post<RewriteDetectionResponse>("/advanced/rewrite-detect", { text });
  return data;
}

// --- Fingerprint ---

export interface FingerprintResponse {
  fingerprintId: string;
  hash: string;
  createdAt: string;
}

export async function generateFingerprint(text: string): Promise<FingerprintResponse> {
  const { data } = await api.post<FingerprintResponse>("/advanced/fingerprint", { text });
  return data;
}

export async function verifyFingerprint(
  fingerprintId1: string,
  fingerprintId2: string
): Promise<{ verified: boolean; similarity: number }> {
  const { data } = await api.post<{ verified: boolean; similarity: number }>(
    "/advanced/fingerprint/verify",
    { fingerprint_id_1: fingerprintId1, fingerprint_id_2: fingerprintId2 }
  );
  return data;
}

// --- Version History ---

export interface VersionEntry {
  id: string;
  versionNumber: number;
  timestamp: string;
  aiScore: number;
  wordCount: number;
  diff?: { type: "added" | "removed" | "unchanged"; text: string }[];
}

export async function submitVersion(
  documentId: string,
  text: string
): Promise<VersionEntry> {
  const { data } = await api.post<VersionEntry>("/advanced/version", {
    document_id: documentId,
    text,
  });
  return data;
}

export async function getVersionHistory(
  documentId: string
): Promise<VersionEntry[]> {
  const { data } = await api.get<VersionEntry[]>(`/advanced/version/${documentId}`);
  return data;
}

// --- Coach / Suggestions ---

export interface CoachSuggestion {
  id: string;
  type: "humanize" | "buzzword" | "grammar" | "readability";
  original: string;
  suggested: string;
  explanation: string;
}

export async function getCoachSuggestions(
  text: string
): Promise<CoachSuggestion[]> {
  const { data } = await api.post<CoachSuggestion[]>("/advanced/coach", { text });
  return data;
}

// --- Batch Processing ---

export interface BatchItemResult {
  id: string;
  filename: string;
  wordCount: number;
  aiScore: number;
  classification: string;
  status: "done" | "error";
  error?: string;
}

export interface BatchResponse {
  batchId: string;
  results: BatchItemResult[];
  summary: {
    totalFiles: number;
    processed: number;
    flagged: number;
    avgScore: number;
  };
}

export async function processBatch(
  items: { filename: string; text: string }[]
): Promise<BatchResponse> {
  const { data } = await api.post<BatchResponse>("/advanced/batch", {
    texts: items.map((item) => item.text),
    filenames: items.map((item) => item.filename),
  });
  return data;
}

export async function getBatchResults(
  batchId: string
): Promise<BatchResponse> {
  const { data } = await api.get<BatchResponse>(`/advanced/batch/${batchId}`);
  return data;
}

// --- Share Analysis ---

export interface ShareAnalysisResponse {
  url: string;
  expiresAt: string | null;
  shareId: string;
}

export async function shareAnalysis(
  analysisData: Record<string, unknown>,
  expiry: "24h" | "7d" | "30d" | "never"
): Promise<ShareAnalysisResponse> {
  const { data } = await api.post<ShareAnalysisResponse>("/advanced/share", {
    analysis_data: analysisData,
    title: `Shared analysis (${expiry})`,
  });
  return data;
}

export default api;
