export interface SignalScore {
  name: string;
  signal?: string;
  score: number;
  ai_probability?: number;
  weight: number;
  description: string;
  category: "statistical" | "linguistic" | "model" | "structural";
  confidence?: string;
  details?: Record<string, unknown>;
}

export interface SentenceScore {
  text: string;
  score: number;
  startIndex: number;
  endIndex: number;
  signals: Record<string, number>;
}

export interface GLTRToken {
  token: string;
  rank: number;
  probability: number;
  entropy: number;
  category: "top10" | "top100" | "top1000" | "rare";
}

export interface DetectionResult {
  id: string;
  text: string;
  overallScore: number;
  confidence: number;
  label: "human" | "ai" | "mixed" | "uncertain";
  signals: SignalScore[];
  sentences: SentenceScore[];
  gltrTokens: GLTRToken[];
  attribution: string;
  wordCount?: number;
  processingTimeMs?: number;
  modelVersion?: string;
  createdAt: string;
}

export interface SourceMatch {
  url: string;
  title: string;
  similarity: number;
  matchedText: string;
  sourceSnippet: string;
}

export interface ParagraphScore {
  text: string;
  score: number;
  sources: SourceMatch[];
}

export interface PlagiarismResult {
  id: string;
  text: string;
  originalityScore: number;
  paragraphs: ParagraphScore[];
  sources: SourceMatch[];
  createdAt: string;
}

export interface HumanizationResult {
  id: string;
  originalText: string;
  humanizedText: string;
  originalScore: number;
  humanizedScore: number;
  meaningPreservation: number;
  style: string;
  iterations: number;
  scoreTimeline: { iteration: number; score: number }[];
  createdAt: string;
}

export interface AnalysisOptions {
  mode?: "quick" | "deep" | "forensic";
  includeGltr?: boolean;
  includeSentences?: boolean;
  model?: string;
}

export interface HistoryItem {
  id: string;
  type: "detection" | "plagiarism" | "humanization";
  textPreview: string;
  score: number;
  label: string;
  createdAt: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
  totalPages: number;
}
