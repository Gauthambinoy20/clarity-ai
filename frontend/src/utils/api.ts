import axios from "axios";
import type {
  DetectionResult,
  SignalScore,
  SentenceScore,
  GLTRToken,
  PlagiarismResult,
  SourceMatch,
  ParagraphScore,
  HumanizationResult,
  AnalysisOptions,
  HistoryItem,
  PaginatedResponse,
} from "@/types/analysis";
import type {
  ReadabilityResult,
  ToneResult,
  GrammarResult,
  GrammarError,
  TextStatistics,
  POSDistribution,
  WritingSuggestionsResult,
  WritingSuggestion,
  CitationResult,
  Citation,
  ComparisonResult,
  DiffSegment,
  FullAnalyticsResult,
} from "@/types/analytics";
import type {
  ApiDetectionResponse,
  ApiSignalResult,
  ApiSentenceScore,
  ApiGltrToken,
  ApiPlagiarismResponse,
  ApiSourceMatch,
  ApiParagraphAnalysis,
  ApiHumanizeResponse,
  ApiHistoryResponse,
  ApiAnalysisSummary,
  ApiDashboardStats,
  ApiDashboardTrends,
  ApiDashboardTopSignals,
  ApiAnalyticsResponse,
  ApiFullAnalyticsResponse,
  ApiReadabilityResults,
  ApiToneResults,
  ApiGrammarResults,
  ApiGrammarIssue,
  ApiStatisticsResults,
  ApiSuggestionsResults,
  ApiWritingSuggestion,
  ApiCitationsResults,
  ApiInlineCitation,
  ApiComparisonResults,
  ApiParaphraseResults,
  ApiFactsResults,
  ApiSeoResults,
  ApiShareLinkResponse,
  ApiRewriteDetectionResponse,
  ApiFingerprintResponse,
  ApiFingerprintVerifyResponse,
  ApiVersionResponse,
  ApiVersionHistoryResponse,
  ApiCoachResponse,
  ApiBatchResponse,
  ApiShareResponse,
} from "@/types/wire";

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

// ---------------------------------------------------------------------------
// Adapter helpers
//
// The backend speaks snake_case wire shapes (see types/wire.ts) and, for the
// analytics routes, wraps the payload in an {analysis_id, results, ...}
// envelope. Everything below maps those shapes onto the camelCase frontend
// types so components never touch raw wire JSON.
// ---------------------------------------------------------------------------

// Friendly classification label used across detection and history.
function mapClassification(classification: string): "human" | "ai" | "mixed" | "uncertain" {
  switch (classification) {
    case "ai_generated":
      return "ai";
    case "human_written":
      return "human";
    case "mixed":
      return "mixed";
    default:
      return "uncertain";
  }
}

// Backend confidence is a coarse label; the UI expects a 0-1 number.
function mapConfidence(confidence: string): number {
  switch (confidence) {
    case "high":
      return 0.95;
    case "medium":
      return 0.7;
    case "low":
      return 0.4;
    default:
      return 0.4;
  }
}

// Detection signals are grouped into UI categories by signal name.
const MODEL_SIGNALS = new Set([
  "gltr",
  "binoculars",
  "fast_detectgpt",
  "ghostbuster",
  "zero_shot_ensemble",
  "multi_model_consensus",
  "sentence_level",
]);
const STATISTICAL_SIGNALS = new Set([
  "perplexity_burstiness",
  "entropy_analyzer",
  "repetition",
  "vocabulary_richness",
  "watermark",
]);
const LINGUISTIC_SIGNALS = new Set([
  "stylometric",
  "pos_patterns",
  "coherence",
  "ai_fingerprint",
  "ai_pattern_database",
]);

function signalCategory(name: string): SignalScore["category"] {
  if (MODEL_SIGNALS.has(name)) return "model";
  if (STATISTICAL_SIGNALS.has(name)) return "statistical";
  if (LINGUISTIC_SIGNALS.has(name)) return "linguistic";
  return "structural";
}

function mapSignal(s: ApiSignalResult): SignalScore {
  return {
    name: s.signal,
    signal: s.signal,
    // ai_probability is the 0-1 score the UI renders; keep both keys.
    score: s.ai_probability,
    ai_probability: s.ai_probability,
    weight: 0, // backend does not expose per-signal weights
    description: "",
    category: signalCategory(s.signal),
    confidence: s.confidence,
    details: s.details ?? undefined,
  };
}

// Sentence spans are resolved against the submitted text via successive
// indexOf so highlight offsets line up with the original input.
function mapSentences(sentences: ApiSentenceScore[], submittedText: string): SentenceScore[] {
  let searchFrom = 0;
  return sentences.map((s) => {
    const start = submittedText.indexOf(s.sentence, searchFrom);
    const startIndex = start >= 0 ? start : searchFrom;
    const endIndex = startIndex + s.sentence.length;
    if (start >= 0) searchFrom = endIndex;
    return {
      text: s.sentence,
      score: s.ai_probability,
      startIndex,
      endIndex,
      signals: {},
    };
  });
}

function mapGltrToken(t: ApiGltrToken): GLTRToken {
  return {
    token: t.token,
    rank: t.rank,
    probability: t.probability,
    entropy: t.entropy,
    category: t.bucket as GLTRToken["category"],
  };
}

function unwrap<T>(envelope: ApiAnalyticsResponse): T {
  return envelope.results as T;
}

// ---------------------------------------------------------------------------
// Detection
// ---------------------------------------------------------------------------

export async function analyzeText(
  text: string,
  mode: string = "deep",
  options?: AnalysisOptions
): Promise<DetectionResult> {
  const { data } = await api.post<ApiDetectionResponse>("/detect", {
    text,
    mode,
    ...options,
  });

  return {
    id: data.analysis_id,
    text,
    // The UI gauge expects a 0-100 score; the wire score is 0-1.
    overallScore: data.overall_score * 100,
    confidence: mapConfidence(data.confidence),
    label: mapClassification(data.classification),
    signals: data.signals.map(mapSignal),
    sentences: mapSentences(data.sentence_analysis ?? [], text),
    gltrTokens: (data.gltr_tokens ?? []).map(mapGltrToken),
    attribution: data.attribution?.likely_model ?? "",
    wordCount: data.word_count,
    processingTimeMs: data.processing_time_ms,
    modelVersion: data.model_version,
    createdAt: new Date().toISOString(),
  };
}

// ---------------------------------------------------------------------------
// Plagiarism
// ---------------------------------------------------------------------------

function mapSource(s: ApiSourceMatch): SourceMatch {
  return {
    url: s.url ?? "",
    title: s.title ?? "",
    similarity: s.similarity_score,
    matchedText: s.matched_text,
    // The wire carries no separate snippet, so reuse the matched text.
    sourceSnippet: s.matched_text,
  };
}

function mapParagraph(p: ApiParagraphAnalysis): ParagraphScore {
  return {
    text: p.text,
    // PlagiarismReport renders paragraph scores as a 0-100 percentage.
    score: p.plagiarism_score * 100,
    sources: p.sources.map(mapSource),
  };
}

export async function analyzePlagiarism(
  text: string,
  options?: AnalysisOptions
): Promise<PlagiarismResult> {
  const { data } = await api.post<ApiPlagiarismResponse>("/plagiarism", {
    text,
    ...options,
  });

  return {
    id: data.result_id,
    text,
    // PlagiarismReport reads originalityScore directly as a 0-100 percentage.
    originalityScore: data.originality_percentage,
    paragraphs: data.paragraph_analysis.map(mapParagraph),
    sources: data.sources_found.map(mapSource),
    createdAt: new Date().toISOString(),
  };
}

// ---------------------------------------------------------------------------
// Humanization
// ---------------------------------------------------------------------------

export async function humanizeText(
  text: string,
  style: string = "academic",
  options?: AnalysisOptions
): Promise<HumanizationResult> {
  const { data } = await api.post<ApiHumanizeResponse>("/humanize", {
    text,
    style,
    ...options,
  });

  return {
    id: data.result_id,
    originalText: data.original_text,
    humanizedText: data.humanized_text,
    // HumanizerPanel renders these as 0-100 percentages; the wire is 0-1.
    originalScore: data.original_ai_score * 100,
    humanizedScore: data.final_ai_score * 100,
    meaningPreservation: data.quality.meaning_preservation,
    // The panel's style toggle reflects the requested style.
    style: data.model_used || style,
    iterations: data.iterations_used,
    scoreTimeline: data.timeline.map((t) => ({
      iteration: t.iteration,
      score: t.ai_score * 100,
    })),
    createdAt: new Date().toISOString(),
  };
}

// ---------------------------------------------------------------------------
// History
// ---------------------------------------------------------------------------

// History summaries carry a backend classification but no preview or type.
function mapHistoryType(classification: string): HistoryItem["type"] {
  if (classification === "humanization") return "humanization";
  if (classification === "plagiarism_check") return "plagiarism";
  return "detection";
}

function historyLabel(classification: string): string {
  if (classification === "humanization") return "humanization";
  if (classification === "plagiarism_check") return "plagiarism";
  return mapClassification(classification);
}

function mapHistoryItem(s: ApiAnalysisSummary): HistoryItem {
  return {
    id: s.analysis_id,
    type: mapHistoryType(s.classification),
    // The wire summary has no text preview; honest empty string.
    textPreview: "",
    score: s.overall_ai_score * 100,
    label: historyLabel(s.classification),
    createdAt: s.created_at,
  };
}

export async function getHistory(
  page: number = 1,
  limit: number = 20
): Promise<PaginatedResponse<HistoryItem>> {
  const { data } = await api.get<ApiHistoryResponse>("/history", {
    params: { page, limit },
  });

  return {
    items: data.results.map(mapHistoryItem),
    total: data.total,
    page: data.page,
    limit: data.limit,
    totalPages: data.total_pages,
  };
}

export async function getHealth(): Promise<{ status: string }> {
  const { data } = await api.get<{ status: string }>("/health");
  return data;
}

// ---------------------------------------------------------------------------
// Analytics endpoints (each wraps its payload in the {results} envelope)
// ---------------------------------------------------------------------------

export async function analyzeReadability(text: string): Promise<ReadabilityResult> {
  const { data } = await api.post<ApiAnalyticsResponse>("/analytics/readability", { text });
  const r = unwrap<ApiReadabilityResults>(data);
  return {
    flesch_reading_ease: r.flesch_reading_ease,
    flesch_kincaid_grade: r.flesch_kincaid_grade,
    gunning_fog: r.gunning_fog_index,
    smog_index: r.smog_index,
    coleman_liau: r.coleman_liau_index,
    automated_readability: r.automated_readability_index,
    dale_chall: r.dale_chall_score,
    // No Linsear Write metric on the wire; leave at 0.
    linsear_write: 0,
    overall_grade: r.overall_grade,
    reading_time_seconds: r.reading_time_minutes * 60,
    reading_time_minutes: r.reading_time_minutes,
    // The wire reports no difficulty band; derive from reading ease.
    difficulty: readingEaseToDifficulty(r.flesch_reading_ease),
  };
}

function readingEaseToDifficulty(ease: number): ReadabilityResult["difficulty"] {
  if (ease >= 80) return "very_easy";
  if (ease >= 60) return "easy";
  if (ease >= 40) return "moderate";
  if (ease >= 20) return "difficult";
  return "very_difficult";
}

export async function analyzeTone(text: string): Promise<ToneResult> {
  const { data } = await api.post<ApiAnalyticsResponse>("/analytics/tone", { text });
  const r = unwrap<ApiToneResults>(data);
  return {
    formality: r.formality_score,
    sentiment: r.sentiment.score,
    sentiment_label: r.sentiment.label as ToneResult["sentiment_label"],
    emotions: Object.entries(r.emotions).map(([emotion, score]) => ({ emotion, score })),
    objectivity: r.objectivity_score,
    persuasiveness: r.persuasiveness_score,
    urgency: r.urgency_level.score,
    // No standalone tone confidence on the wire; objectivity is the closest proxy.
    confidence: r.objectivity_score,
  };
}

function mapGrammarError(e: ApiGrammarIssue, index: number): GrammarError {
  return {
    id: `grammar-${index}`,
    message: e.message,
    context: "",
    offset: e.position?.start ?? 0,
    length: e.position?.end != null ? e.position.end - (e.position.start ?? 0) : 0,
    original: "",
    suggestions: e.suggestion ? [e.suggestion] : [],
    severity: e.type === "style" ? "warning" : "error",
    category: e.type ?? "grammar",
    rule_id: "",
  };
}

export async function checkGrammar(text: string): Promise<GrammarResult> {
  const { data } = await api.post<ApiAnalyticsResponse>("/analytics/grammar", { text });
  const r = unwrap<ApiGrammarResults>(data);
  return {
    errors: r.errors.map(mapGrammarError),
    grammar_score: r.grammar_score,
    style_score: r.style_score,
    total_errors: r.error_count + r.style_issue_count,
    category_counts: {
      grammar: r.error_count,
      style: r.style_issue_count,
    },
    // The wire returns no corrected text.
    corrected_text: "",
  };
}

function mapPosDistribution(pos: ApiStatisticsResults["pos_distribution"]): POSDistribution[] {
  return Object.entries(pos).map(([tag, val]) => ({
    tag,
    label: tag,
    count: val.count,
  }));
}

export async function getStatistics(text: string): Promise<TextStatistics> {
  const { data } = await api.post<ApiAnalyticsResponse>("/analytics/statistics", { text });
  const r = unwrap<ApiStatisticsResults>(data);
  return {
    word_count: r.word_count,
    sentence_count: r.sentence_count,
    paragraph_count: r.paragraph_count,
    character_count: r.character_count_with_spaces,
    character_count_no_spaces: r.character_count_without_spaces,
    unique_word_count: r.unique_words,
    avg_word_length: r.avg_word_length,
    avg_sentence_length: r.avg_sentence_length,
    vocabulary_richness: r.vocabulary_richness,
    reading_time_minutes: r.reading_time_minutes,
    speaking_time_minutes: r.speaking_time_minutes,
    word_length_distribution: r.word_length_distribution,
    sentence_length_distribution: r.sentence_length_distribution,
    pos_distribution: mapPosDistribution(r.pos_distribution),
    word_cloud_data: r.word_cloud_data.map((w) => ({ text: w.word, value: w.frequency })),
    common_words: r.most_common_words,
  };
}

function mapWritingSuggestion(s: ApiWritingSuggestion, index: number): WritingSuggestion {
  return {
    id: `suggestion-${index}`,
    category: s.category as WritingSuggestion["category"],
    severity: mapSuggestionSeverity(s.severity),
    message: s.message,
    original: s.original_text ?? "",
    suggested: s.suggested_fix ?? "",
    // The wire carries no separate explanation; the message is the guidance.
    explanation: s.message,
    position: { start: s.position?.start ?? 0, end: s.position?.end ?? 0 },
  };
}

function mapSuggestionSeverity(severity: string): WritingSuggestion["severity"] {
  if (severity === "error") return "high";
  if (severity === "warning") return "medium";
  return "low";
}

export async function getSuggestions(text: string): Promise<WritingSuggestionsResult> {
  const { data } = await api.post<ApiAnalyticsResponse>("/analytics/suggestions", { text });
  const r = unwrap<ApiSuggestionsResults>(data);
  return {
    suggestions: r.suggestions.map(mapWritingSuggestion),
    overall_score: r.overall_writing_score,
    category_scores: r.category_breakdown,
  };
}

function mapCitation(c: ApiInlineCitation, index: number): Citation {
  return {
    id: `citation-${index}`,
    text: c.text,
    style_detected: c.style,
    // The extractor does not validate inline citations individually.
    is_valid: true,
    issues: [],
    authors: [],
    year: c.year,
    title: c.title,
  };
}

export async function extractCitations(text: string): Promise<CitationResult> {
  const { data } = await api.post<ApiAnalyticsResponse>("/analytics/citations", { text });
  const r = unwrap<ApiCitationsResults>(data);
  return {
    citations: r.inline_citations.map(mapCitation),
    detected_style: r.citation_style,
    total_citations: r.citations_found,
    valid_count: r.citations_found,
    invalid_count: 0,
    missing_references: r.missing_references,
    // No consistency score on the wire; report a clean score when no issues.
    format_consistency_score: r.format_issues.length === 0 ? 100 : 0,
    issues: r.format_issues,
  };
}

function mapComparison(r: ApiComparisonResults): ComparisonResult {
  return {
    similarity_score: r.similarity_score,
    diff_data: r.diff_data.map(
      (d): DiffSegment => ({
        type: d.type as DiffSegment["type"],
        text: d.text,
        text_b: d.text_b,
      })
    ),
    common_phrases: r.common_phrases,
    text_a_stats: r.structural_comparison.text_a,
    text_b_stats: r.structural_comparison.text_b,
    vocabulary_overlap: r.structural_comparison.vocabulary_overlap,
  };
}

export async function compareTexts(textA: string, textB: string): Promise<ComparisonResult> {
  const { data } = await api.post<ApiAnalyticsResponse>("/analytics/compare", {
    text_a: textA,
    text_b: textB,
  });
  return mapComparison(unwrap<ApiComparisonResults>(data));
}

export async function runFullAnalytics(text: string): Promise<FullAnalyticsResult> {
  const { data } = await api.post<ApiFullAnalyticsResponse>("/analytics/full", { text });
  return {
    readability: mapReadabilityResults(data.readability as unknown as ApiReadabilityResults),
    tone: mapToneResults(data.tone as unknown as ApiToneResults),
    grammar: mapGrammarResults(data.grammar as unknown as ApiGrammarResults),
    statistics: mapStatisticsResults(data.statistics as unknown as ApiStatisticsResults),
    suggestions: mapSuggestionsResults(data.suggestions as unknown as ApiSuggestionsResults),
    // The /full route does not run the citation extractor; honest empty result.
    citations: {
      citations: [],
      detected_style: "unknown",
      total_citations: 0,
      valid_count: 0,
      invalid_count: 0,
      missing_references: [],
      format_consistency_score: 100,
      issues: [],
    },
  };
}

// Reusable payload->type mappers shared by /full (it returns each payload
// directly, without the single-result envelope).
function mapReadabilityResults(r: ApiReadabilityResults): ReadabilityResult {
  return {
    flesch_reading_ease: r.flesch_reading_ease,
    flesch_kincaid_grade: r.flesch_kincaid_grade,
    gunning_fog: r.gunning_fog_index,
    smog_index: r.smog_index,
    coleman_liau: r.coleman_liau_index,
    automated_readability: r.automated_readability_index,
    dale_chall: r.dale_chall_score,
    linsear_write: 0,
    overall_grade: r.overall_grade,
    reading_time_seconds: r.reading_time_minutes * 60,
    reading_time_minutes: r.reading_time_minutes,
    difficulty: readingEaseToDifficulty(r.flesch_reading_ease),
  };
}

function mapToneResults(r: ApiToneResults): ToneResult {
  return {
    formality: r.formality_score,
    sentiment: r.sentiment.score,
    sentiment_label: r.sentiment.label as ToneResult["sentiment_label"],
    emotions: Object.entries(r.emotions).map(([emotion, score]) => ({ emotion, score })),
    objectivity: r.objectivity_score,
    persuasiveness: r.persuasiveness_score,
    urgency: r.urgency_level.score,
    confidence: r.objectivity_score,
  };
}

function mapGrammarResults(r: ApiGrammarResults): GrammarResult {
  return {
    errors: r.errors.map(mapGrammarError),
    grammar_score: r.grammar_score,
    style_score: r.style_score,
    total_errors: r.error_count + r.style_issue_count,
    category_counts: { grammar: r.error_count, style: r.style_issue_count },
    corrected_text: "",
  };
}

function mapStatisticsResults(r: ApiStatisticsResults): TextStatistics {
  return {
    word_count: r.word_count,
    sentence_count: r.sentence_count,
    paragraph_count: r.paragraph_count,
    character_count: r.character_count_with_spaces,
    character_count_no_spaces: r.character_count_without_spaces,
    unique_word_count: r.unique_words,
    avg_word_length: r.avg_word_length,
    avg_sentence_length: r.avg_sentence_length,
    vocabulary_richness: r.vocabulary_richness,
    reading_time_minutes: r.reading_time_minutes,
    speaking_time_minutes: r.speaking_time_minutes,
    word_length_distribution: r.word_length_distribution,
    sentence_length_distribution: r.sentence_length_distribution,
    pos_distribution: mapPosDistribution(r.pos_distribution),
    word_cloud_data: r.word_cloud_data.map((w) => ({ text: w.word, value: w.frequency })),
    common_words: r.most_common_words,
  };
}

function mapSuggestionsResults(r: ApiSuggestionsResults): WritingSuggestionsResult {
  return {
    suggestions: r.suggestions.map(mapWritingSuggestion),
    overall_score: r.overall_writing_score,
    category_scores: r.category_breakdown,
  };
}

// ---------------------------------------------------------------------------
// Export endpoints
// ---------------------------------------------------------------------------

export async function exportPdf(data: Record<string, unknown>, text: string): Promise<Blob> {
  const response = await api.post("/export/pdf", { data, text }, { responseType: "blob" });
  return response.data;
}

export async function exportJson(data: Record<string, unknown>): Promise<Blob> {
  const response = await api.post("/export/json", { data }, { responseType: "blob" });
  return response.data;
}

export async function exportCsv(data: Record<string, unknown>): Promise<Blob> {
  const response = await api.post("/export/csv", { data }, { responseType: "blob" });
  return response.data;
}

export async function getShareLink(data: Record<string, unknown>): Promise<{ url: string }> {
  const { data: result } = await api.post<ApiShareLinkResponse>("/export/share", {
    data,
  });
  return { url: result.url };
}

// --- Paraphrase / Fact Check / SEO / Dashboard endpoints ---

import type {
  ParaphraseResult,
  SentencePair,
  SentenceCluster,
  FactCheckResult,
  Claim,
  SEOResult,
  KeywordEntry,
  SEOMetric,
  SEORecommendation,
  DashboardStats,
  DashboardTrends,
  TopSignal,
} from "@/types/analytics";

function mapSentencePair(p: ApiParaphraseResults["flagged_pairs"][number]): SentencePair {
  return {
    sentenceA: p.sentence_a,
    sentenceB: p.sentence_b,
    similarity: p.similarity,
    indexA: p.sentence_a_index,
    indexB: p.sentence_b_index,
  };
}

function mapCluster(c: ApiParaphraseResults["clusters"][number]): SentenceCluster {
  return {
    label: `Cluster ${c.cluster_id + 1}`,
    sentences: [c.representative],
    // The wire reports cluster membership, not a pairwise similarity score.
    avgSimilarity: 1,
  };
}

export async function analyzeParaphrase(text: string): Promise<ParaphraseResult> {
  const { data } = await api.post<ApiAnalyticsResponse>("/analytics/paraphrase", { text });
  const r = unwrap<ApiParaphraseResults>(data);
  const uniqueSentences = Math.round(r.unique_content_ratio * r.total_sentences);
  return {
    uniqueContentRatio: r.unique_content_ratio,
    flaggedPairs: r.flagged_pairs.map(mapSentencePair),
    clusters: r.clusters.map(mapCluster),
    totalSentences: r.total_sentences,
    uniqueSentences,
  };
}

function mapClaim(c: ApiFactsResults["claims_found"][number], index: number): Claim {
  return {
    id: `claim-${index}`,
    text: c.text,
    category: c.category as Claim["category"],
    verified: c.verifiable ?? false,
    // The detector flags verifiability, not a numeric confidence.
    confidence: c.verifiable ? 1 : 0,
    // No source attribution on the wire; leave undefined (Claim.source is optional).
  };
}

export async function checkFacts(text: string): Promise<FactCheckResult> {
  const { data } = await api.post<ApiAnalyticsResponse>("/analytics/facts", { text });
  const r = unwrap<ApiFactsResults>(data);
  return {
    credibilityScore: r.credibility_score,
    claims: r.claims_found.map(mapClaim),
    vagueAttributions: r.vague_claims_count,
    factualDensity: r.factual_density,
    // No standalone tips field; surface the vague-claim texts as guidance.
    tips: r.vague_claims.map((v) => v.text),
  };
}

function seoGrade(score: number): SEOResult["grade"] {
  if (score >= 90) return "A";
  if (score >= 80) return "B";
  if (score >= 70) return "C";
  if (score >= 60) return "D";
  return "F";
}

function mapSeoKeyword(k: ApiSeoResults["keyword_analysis"][number]): KeywordEntry {
  return {
    keyword: k.keyword,
    count: k.frequency,
    density: k.density_percent,
  };
}

// SEO metrics are flattened from the backend's metrics block into the
// pass/target rows the UI table renders.
function mapSeoMetrics(m: ApiSeoResults["metrics"]): SEOMetric[] {
  return [
    {
      name: "Word Count",
      value: m.word_count,
      target: "300+ words",
      pass: m.word_count >= 300,
      unit: "words",
    },
    {
      name: "Transition Words",
      value: m.transition_word_percentage,
      target: ">25%",
      pass: m.transition_word_percentage > 25,
      unit: "%",
    },
    {
      name: "Passive Voice",
      value: m.passive_voice_percentage,
      target: "<15%",
      pass: m.passive_voice_percentage < 15,
      unit: "%",
    },
    {
      name: "Avg Sentence Length",
      value: m.avg_sentence_length,
      target: "<20 words",
      pass: m.avg_sentence_length < 20,
      unit: "words",
    },
    {
      name: "Headings",
      value: m.heading_count,
      target: "1+",
      pass: m.heading_count >= 1,
      unit: "",
    },
    {
      name: "Reading Ease",
      value: m.flesch_reading_ease,
      target: "60+",
      pass: m.flesch_reading_ease >= 60,
      unit: "",
    },
  ];
}

export async function analyzeSEO(text: string): Promise<SEOResult> {
  const { data } = await api.post<ApiAnalyticsResponse>("/analytics/seo", { text });
  const r = unwrap<ApiSeoResults>(data);
  return {
    seoScore: r.seo_score,
    grade: seoGrade(r.seo_score),
    keywords: r.keyword_analysis.map(mapSeoKeyword),
    metrics: mapSeoMetrics(r.metrics),
    // The backend returns plain recommendation strings without a priority.
    recommendations: r.recommendations.map(
      (text): SEORecommendation => ({ text, priority: "medium" })
    ),
  };
}

export async function getDashboardStats(): Promise<DashboardStats> {
  const { data } = await api.get<ApiDashboardStats>("/dashboard/stats");
  return {
    totalAnalyses: data.total_analyses,
    // the stat card renders this raw, so scale to the 0-100 range like
    // every other score in the app
    avgAiScore: Math.round(data.average_ai_score * 100),
    totalWords: data.total_words_analyzed,
    analysesToday: data.analyses_today,
  };
}

export async function getDashboardTrends(): Promise<DashboardTrends> {
  const { data } = await api.get<ApiDashboardTrends>("/dashboard/trends");
  return {
    scoreDistribution: data.ai_score_histogram.map((b) => ({
      range: `${Math.round(b.bin_start * 100)}-${Math.round(b.bin_end * 100)}`,
      count: b.count,
    })),
    analysesPerDay: data.analyses_per_day.map((p) => ({ date: p.date, count: p.count })),
    classificationBreakdown: data.most_common_classifications.map((c) => ({
      label: historyLabel(c.classification),
      value: c.count,
    })),
    // The trends route does not return recent analyses.
    recentAnalyses: [],
  };
}

export async function getTopSignals(limit: number = 10): Promise<TopSignal[]> {
  const { data } = await api.get<ApiDashboardTopSignals>("/dashboard/top-signals", {
    params: { limit },
  });
  return data.signals.slice(0, limit).map((s) => ({
    name: s.signal_name,
    count: s.fire_count,
  }));
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

// Turn a snake_case pattern key into a readable label.
function humanizePatternKey(key: string): string {
  return key
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

export async function detectRewrite(text: string): Promise<RewriteDetectionResponse> {
  const { data } = await api.post<ApiRewriteDetectionResponse>("/advanced/rewrite-detect", {
    text,
  });
  return {
    isRewritten: data.rewrite_detected,
    // naturalness_score is already on a 0-100 scale.
    naturalnessScore: data.naturalness_score,
    confidence: data.rewrite_confidence,
    residualPatterns: data.residual_ai_patterns.map((key, index) => ({
      id: `pattern-${index}`,
      pattern: humanizePatternKey(key),
      // The wire lists pattern keys only; no per-pattern description or count.
      description: "",
      severity: "medium",
      count: 1,
    })),
    // No prose explanation on the wire; the UI falls back to its own copy.
    explanation: "",
  };
}

// --- Fingerprint ---

export interface FingerprintResponse {
  fingerprintId: string;
  hash: string;
  createdAt: string;
}

export async function generateFingerprint(text: string): Promise<FingerprintResponse> {
  const { data } = await api.post<ApiFingerprintResponse>("/advanced/fingerprint", { text });
  return {
    fingerprintId: data.fingerprint_id,
    hash: data.text_hash,
    createdAt: data.created_at,
  };
}

export async function verifyFingerprint(
  fingerprintId1: string,
  fingerprintId2: string
): Promise<{ verified: boolean; similarity: number }> {
  const { data } = await api.post<ApiFingerprintVerifyResponse>("/advanced/fingerprint/verify", {
    fingerprint_id_1: fingerprintId1,
    fingerprint_id_2: fingerprintId2,
  });
  return {
    verified: data.exact_match || data.content_match,
    similarity: data.content_similarity,
  };
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

export async function submitVersion(documentId: string, text: string): Promise<VersionEntry> {
  const { data } = await api.post<ApiVersionResponse>("/advanced/version", {
    document_id: documentId,
    text,
  });
  return {
    id: `${data.document_id}-v${data.version_number}`,
    versionNumber: data.version_number,
    // POST /version returns no timestamp; stamp it client-side.
    timestamp: new Date().toISOString(),
    // The UI renders aiScore as a 0-100 percentage; the wire score is 0-1.
    aiScore: Math.round(data.current_score * 100),
    // No word count on the submit response; derive from the diff summary.
    wordCount: (data.diff_summary.words_added ?? 0) + (data.diff_summary.words_changed ?? 0),
    // diff_summary holds counts, not text segments, so no inline diff here.
    diff: undefined,
  };
}

export async function getVersionHistory(documentId: string): Promise<VersionEntry[]> {
  const { data } = await api.get<ApiVersionHistoryResponse>(`/advanced/version/${documentId}`);
  return data.versions.map((v) => ({
    id: `${data.document_id}-v${v.version_number}`,
    versionNumber: v.version_number,
    timestamp: v.timestamp,
    aiScore: Math.round(v.ai_score * 100),
    wordCount: v.word_count,
    // Stored versions keep diff counts only, not text segments.
    diff: undefined,
  }));
}

// --- Coach / Suggestions ---

export interface CoachSuggestion {
  id: string;
  type: "humanize" | "buzzword" | "grammar" | "readability";
  original: string;
  suggested: string;
  explanation: string;
}

// Map the backend's coach category onto the UI's suggestion type.
function mapCoachType(category: string): CoachSuggestion["type"] {
  switch (category) {
    case "contraction":
    case "sentence_structure":
      return "readability";
    case "buzzword":
      return "buzzword";
    case "grammar":
      return "grammar";
    default:
      return "humanize";
  }
}

export async function getCoachSuggestions(text: string): Promise<CoachSuggestion[]> {
  const { data } = await api.post<ApiCoachResponse>("/advanced/coach", { text });
  return data.suggestions.map((s, index) => ({
    id: `coach-${index}`,
    type: mapCoachType(s.category),
    original: s.original ?? "",
    suggested: s.fix ?? "",
    explanation: s.message,
  }));
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

function mapBatchResponse(data: ApiBatchResponse): BatchResponse {
  return {
    batchId: data.batch_id,
    results: data.results.map((r) => ({
      id: `${data.batch_id}-${r.index}`,
      filename: r.filename,
      wordCount: r.word_count,
      // The UI renders aiScore as a 0-100 percentage; the wire score is 0-1.
      aiScore: Math.round(r.ai_score * 100),
      classification: r.classification,
      status: "done",
    })),
    summary: {
      totalFiles: data.total_files,
      // Every returned item processed successfully (failures are dropped).
      processed: data.results.length,
      flagged: data.flagged_count,
      avgScore: Math.round(data.avg_score * 100),
    },
  };
}

export async function processBatch(
  items: { filename: string; text: string }[]
): Promise<BatchResponse> {
  const { data } = await api.post<ApiBatchResponse>("/advanced/batch", {
    texts: items.map((item) => item.text),
    filenames: items.map((item) => item.filename),
  });
  return mapBatchResponse(data);
}

export async function getBatchResults(batchId: string): Promise<BatchResponse> {
  const { data } = await api.get<ApiBatchResponse>(`/advanced/batch/${batchId}`);
  return mapBatchResponse(data);
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
  const { data } = await api.post<ApiShareResponse>("/advanced/share", {
    analysis_data: analysisData,
    title: `Shared analysis (${expiry})`,
  });
  return {
    url: data.share_url,
    // The backend stores no expiry; the requested window is informational.
    expiresAt: null,
    shareId: data.share_token,
  };
}

export default api;
