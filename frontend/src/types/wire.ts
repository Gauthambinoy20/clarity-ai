/**
 * Wire types — the exact JSON shapes the FastAPI backend returns.
 *
 * These mirror the pydantic response models in backend/app/api/routes/*.py
 * field-for-field (snake_case, optionals, nesting). They exist so the adapter
 * functions in utils/api.ts have a typed source to map FROM. Nothing outside
 * the adapter layer should import these — the rest of the app speaks the
 * camelCase frontend types in types/analysis.ts and types/analytics.ts.
 */

// ── Detection (backend/app/api/routes/detection.py) ──────────────────

export interface ApiSignalResult {
  signal: string;
  ai_probability: number;
  confidence: string;
  details?: Record<string, unknown> | null;
}

export interface ApiSentenceScore {
  sentence: string;
  ai_probability: number;
  highlight: string; // "high" | "medium" | "low"
}

export interface ApiGltrToken {
  token: string;
  token_id?: number;
  rank: number;
  probability: number;
  entropy: number;
  bucket: string; // "top10" | "top100" | "top1000" | "rare"
  color?: string;
}

export interface ApiAttribution {
  likely_model: string;
  model_confidence?: number | null;
  all_model_scores?: { model: string; score: number }[];
}

export interface ApiDetectionResponse {
  analysis_id: string;
  overall_score: number;
  classification: string;
  confidence: string;
  signals: ApiSignalResult[];
  sentence_analysis?: ApiSentenceScore[] | null;
  gltr_tokens?: ApiGltrToken[] | null;
  attribution?: ApiAttribution | null;
  word_count: number;
  processing_time_ms: number;
  model_version: string;
}

// ── Plagiarism (backend/app/api/routes/plagiarism.py) ────────────────

export interface ApiSourceMatch {
  url?: string | null;
  title?: string | null;
  matched_text: string;
  similarity_score: number;
  method: string; // "exact" | "fuzzy" | "semantic"
}

export interface ApiParagraphAnalysis {
  paragraph_index: number;
  text: string;
  plagiarism_score: number;
  sources: ApiSourceMatch[];
}

export interface ApiPlagiarismResponse {
  result_id: string;
  overall_plagiarism_score: number;
  originality_percentage: number;
  paragraph_analysis: ApiParagraphAnalysis[];
  sources_found: ApiSourceMatch[];
  total_sources: number;
  word_count: number;
  processing_time_ms: number;
}

// ── Humanization (backend/app/api/routes/humanization.py) ────────────

export interface ApiIterationSnapshot {
  iteration: number;
  ai_score: number;
  plagiarism_score: number;
  text_preview: string;
}

export interface ApiQualityMetrics {
  readability_score: number;
  vocabulary_diversity: number;
  sentence_variety: number;
  meaning_preservation: number;
}

export interface ApiHumanizeResponse {
  result_id: string;
  original_text: string;
  humanized_text: string;
  original_ai_score: number;
  final_ai_score: number;
  original_plagiarism_score: number;
  final_plagiarism_score: number;
  iterations_used: number;
  timeline: ApiIterationSnapshot[];
  quality: ApiQualityMetrics;
  model_used: string;
  processing_time_ms: number;
}

// ── History (backend/app/api/routes/health.py) ───────────────────────

export interface ApiAnalysisSummary {
  analysis_id: string;
  classification: string;
  overall_ai_score: number;
  word_count: number;
  processing_time_ms: number;
  model_version: string;
  created_at: string;
}

export interface ApiHistoryResponse {
  page: number;
  limit: number;
  total: number;
  total_pages: number;
  results: ApiAnalysisSummary[];
}

// ── Dashboard (backend/app/api/routes/dashboard.py) ──────────────────

export interface ApiDashboardStats {
  total_analyses: number;
  average_ai_score: number;
  total_words_analyzed: number;
  analyses_today: number;
  analyses_this_week: number;
  analyses_this_month: number;
}

export interface ApiHistogramBin {
  bin_start: number;
  bin_end: number;
  count: number;
}

export interface ApiTrendPoint {
  date: string;
  count: number;
}

export interface ApiClassificationCount {
  classification: string;
  count: number;
}

export interface ApiDashboardTrends {
  ai_score_histogram: ApiHistogramBin[];
  analyses_per_day: ApiTrendPoint[];
  most_common_classifications: ApiClassificationCount[];
}

export interface ApiSignalStat {
  signal_name: string;
  fire_count: number;
  average_score: number;
}

export interface ApiDashboardTopSignals {
  signals: ApiSignalStat[];
}

// ── Analytics (backend/app/api/routes/analytics.py) ──────────────────
//
// Every /analytics/* route wraps the analyzer output in this envelope; the
// real payload lives under `results` and uses the analyzer's own key names.

export interface ApiAnalyticsResponse {
  analysis_id: string;
  analysis_type: string;
  results: Record<string, unknown>;
  processing_time_ms: number;
}

export interface ApiFullAnalyticsResponse {
  analysis_id: string;
  readability: Record<string, unknown>;
  tone: Record<string, unknown>;
  grammar: Record<string, unknown>;
  statistics: Record<string, unknown>;
  suggestions: Record<string, unknown>;
  processing_time_ms: number;
}

// The analyzer payloads (the `results` dict), keyed by their own names. These
// mirror the dicts returned by app/ml/analyzers/*.py.

export interface ApiReadabilityResults {
  flesch_kincaid_grade: number;
  flesch_reading_ease: number;
  gunning_fog_index: number;
  coleman_liau_index: number;
  smog_index: number;
  automated_readability_index: number;
  dale_chall_score: number;
  avg_words_per_sentence: number;
  avg_syllables_per_word: number;
  reading_time_minutes: number;
  overall_grade: string;
  word_count: number;
  sentence_count: number;
  difficult_word_count: number;
  polysyllabic_word_count: number;
}

export interface ApiToneResults {
  formality_score: number;
  sentiment: { label: string; score: number; positive_count: number; negative_count: number };
  emotions: Record<string, number>;
  objectivity_score: number;
  persuasiveness_score: number;
  urgency_level: { level: string; score: number; urgent_word_count: number };
  professional_casual_score: number;
}

export interface ApiGrammarIssue {
  type?: string; // "grammar" | "style"
  message: string;
  position?: { start: number; end?: number } | null;
  suggestion?: string;
}

export interface ApiGrammarResults {
  error_count: number;
  style_issue_count: number;
  errors: ApiGrammarIssue[];
  grammar_score: number;
  style_score: number;
  passive_voice_percentage: number;
}

export interface ApiStatisticsResults {
  word_count: number;
  character_count_with_spaces: number;
  character_count_without_spaces: number;
  sentence_count: number;
  paragraph_count: number;
  avg_word_length: number;
  avg_sentence_length: number;
  unique_words: number;
  vocabulary_richness: number;
  most_common_words: { word: string; count: number }[];
  most_common_bigrams: unknown[];
  word_length_distribution: { length: number; count: number }[];
  sentence_length_distribution: { length: number; count: number }[];
  // Live shape is a dict keyed by part-of-speech name -> {count, percentage}.
  pos_distribution: Record<string, { count: number; percentage: number }>;
  // Live items are {word, frequency}, not {text, value}.
  word_cloud_data: { word: string; frequency: number }[];
  reading_time_minutes: number;
  speaking_time_minutes: number;
  detected_language: { language: string; confidence: number };
}

export interface ApiWritingSuggestion {
  category: string;
  severity: string; // "info" | "warning" | "error" backend-side
  message: string;
  // The live engine also returns these; they feed the frontend original/suggested fields.
  original_text?: string | null;
  suggested_fix?: string | null;
  position?: { start: number; end?: number } | null;
}

export interface ApiSuggestionsResults {
  overall_writing_score: number;
  suggestion_count: number;
  suggestions: ApiWritingSuggestion[];
  category_breakdown: Record<string, number>;
}

export interface ApiInlineCitation {
  text: string;
  style: string;
  year?: string;
  title?: string;
}

export interface ApiCitationsResults {
  citations_found: number;
  citation_style: string;
  inline_citations: ApiInlineCitation[];
  references: { text: string; year?: string; title?: string; style?: string }[];
  reference_count: number;
  missing_references: string[];
  format_issues: string[];
}

export interface ApiComparisonResults {
  similarity_score: number;
  cosine_similarity: number;
  jaccard_similarity: number;
  edit_distance_ratio: number;
  common_phrases: string[];
  diff_data: { type: string; text: string; text_b?: string }[];
  structural_comparison: {
    text_a: {
      word_count: number;
      sentence_count: number;
      avg_sentence_length: number;
      vocabulary_size: number;
    };
    text_b: {
      word_count: number;
      sentence_count: number;
      avg_sentence_length: number;
      vocabulary_size: number;
    };
    vocabulary_overlap: number;
  };
}

export interface ApiParaphraseResults {
  repetition_score: number;
  flagged_pairs: {
    sentence_a_index: number;
    sentence_b_index: number;
    sentence_a: string;
    sentence_b: string;
    similarity: number;
    flag: string;
  }[];
  self_plagiarism_pairs: {
    sentence_a_index: number;
    sentence_b_index: number;
    sentence_a: string;
    sentence_b: string;
    similarity: number;
    flag: string;
  }[];
  clusters: {
    cluster_id: number;
    sentence_indices: number[];
    size: number;
    representative: string;
  }[];
  unique_content_ratio: number;
  total_sentences: number;
  paragraph_count: number;
}

export interface ApiFactClaim {
  text: string;
  category: string;
  // The detector tags spaCy entity type + char span; there is no confidence/source.
  entity_type?: string;
  start?: number;
  end?: number;
  verifiable?: boolean;
}

export interface ApiFactsResults {
  claims_found: ApiFactClaim[];
  vague_claims: { text: string; type?: string }[];
  vague_claims_count: number;
  verifiable_claims_count: number;
  factual_density: number;
  credibility_score: number;
  claim_categories: Record<string, number>;
}

export interface ApiSeoKeyword {
  keyword: string;
  frequency: number;
  density_percent: number;
}

export interface ApiSeoResults {
  seo_score: number;
  keyword_analysis: ApiSeoKeyword[];
  recommendations: string[];
  metrics: {
    word_count: number;
    sentence_count: number;
    paragraph_count: number;
    heading_count: number;
    flesch_reading_ease: number;
    avg_paragraph_sentences: number;
    transition_word_percentage: number;
    passive_voice_percentage: number;
    avg_sentence_length: number;
    long_sentence_count: number;
    meta_description_length: number;
    meta_description_ideal: boolean;
  };
  headings: { level: number; text: string }[];
}

// ── Export / share (backend/app/api/routes/export.py) ────────────────

// POST /export/share returns this lightweight ad-hoc shape.
export interface ApiShareLinkResponse {
  url: string;
  share_token: string;
}

// ── Advanced (backend/app/api/routes/advanced.py) ────────────────────

export interface ApiRewriteDetectionResponse {
  signal: string;
  ai_probability: number;
  confidence: string;
  rewrite_detected: boolean;
  rewrite_confidence: number;
  residual_ai_patterns: string[]; // snake_case pattern keys, e.g. "topic_sentence_pattern"
  naturalness_score: number; // already on a 0-100 scale
  details: Record<string, unknown>;
}

export interface ApiFingerprintResponse {
  fingerprint_id: string;
  text_hash: string;
  content_hash: string;
  structure_hash: string;
  created_at: string;
  word_count: number;
}

export interface ApiFingerprintVerifyResponse {
  exact_match: boolean;
  content_match: boolean;
  structure_match: boolean;
  content_similarity: number;
  fp1_id?: string | null;
  fp2_id?: string | null;
}

export interface ApiVersionResponse {
  document_id: string;
  version_number: number;
  previous_score?: number | null;
  current_score: number; // 0-1 scale
  score_change: number;
  diff_summary: Record<string, number>; // {words_added, words_removed, words_changed}
  score_trajectory: { version: number; score: number; timestamp: string }[];
  total_versions: number;
}

export interface ApiVersionSummary {
  version_number: number;
  ai_score: number; // 0-1 scale
  timestamp: string;
  word_count: number;
  diff_summary: Record<string, number>;
}

export interface ApiVersionHistoryResponse {
  document_id: string;
  total_versions: number;
  latest_version: number;
  latest_score?: number | null;
  score_trajectory: { version: number; score: number; timestamp: string }[];
  versions: ApiVersionSummary[];
}

export interface ApiCoachSuggestion {
  category: string;
  message: string;
  original?: string | null;
  fix?: string | null;
  impact: string; // "high" | "medium" | "low"
  position?: number | null;
}

export interface ApiCoachResponse {
  human_score: number; // 0-100
  suggestions: ApiCoachSuggestion[];
  quick_fixes: Record<string, unknown>[];
  total_suggestions: number;
  high_impact_count: number;
  medium_impact_count: number;
  low_impact_count: number;
}

export interface ApiBatchResultItem {
  index: number;
  filename: string;
  word_count: number;
  ai_score: number; // 0-1 scale
  classification: string;
  top_signal: string;
}

export interface ApiBatchResponse {
  batch_id: string;
  total_files: number;
  avg_score: number; // 0-1 scale
  score_distribution: Record<string, unknown>[];
  flagged_count: number;
  results: ApiBatchResultItem[];
  processing_time_ms: number;
}

export interface ApiShareResponse {
  share_url: string;
  share_token: string;
  qr_code_data: string;
}
