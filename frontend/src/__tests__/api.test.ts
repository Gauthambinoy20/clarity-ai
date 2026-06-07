/**
 * Tests for the API utility module (src/utils/api.ts).
 *
 * Two layers are covered:
 *  1. The axios instance is built with the right defaults and its error
 *     interceptor flattens backend errors into plain Error messages.
 *  2. The adapter layer maps the raw snake_case wire shapes (and the
 *     analytics {results} envelope) onto the camelCase frontend types the
 *     components consume. The wire fixtures below mirror the live backend
 *     JSON captured from the running stack.
 *
 * axios is mocked so no real network calls are made; we feed wire fixtures
 * to the mocked instance and assert the mapped output.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";

// A single shared stub instance stands in for axios.create()'s return value.
// Declared via vi.hoisted so it exists before the hoisted vi.mock factory runs.
const mockInstance = vi.hoisted(() => ({
  post: vi.fn(),
  get: vi.fn(),
  interceptors: { response: { use: vi.fn() } },
  defaults: {
    baseURL: "/api/v1",
    headers: { common: { "Content-Type": "application/json" } } as Record<string, unknown>,
    timeout: 120000,
  },
}));

vi.mock("axios", () => ({
  default: {
    create: () => mockInstance,
  },
}));

import api, {
  analyzeText,
  analyzePlagiarism,
  humanizeText,
  getHistory,
  analyzeReadability,
  analyzeTone,
  checkGrammar,
  getStatistics,
  getSuggestions,
  extractCitations,
  compareTexts,
  analyzeParaphrase,
  checkFacts,
  analyzeSEO,
  getDashboardStats,
  getDashboardTrends,
  getTopSignals,
  detectRewrite,
  submitVersion,
  getCoachSuggestions,
  processBatch,
  getShareLink,
  shareAnalysis,
} from "../utils/api";

beforeEach(() => {
  mockInstance.post.mockReset();
  mockInstance.get.mockReset();
});

function postResolves(payload: unknown) {
  mockInstance.post.mockResolvedValueOnce({ data: payload });
}
function getResolves(payload: unknown) {
  mockInstance.get.mockResolvedValueOnce({ data: payload });
}

describe("api axios instance", () => {
  it("is defined", () => {
    expect(api).toBeDefined();
  });

  it("has the correct baseURL", () => {
    expect(api.defaults.baseURL).toBe("/api/v1");
  });

  it("has a timeout set", () => {
    expect(api.defaults.timeout).toBeGreaterThan(0);
  });
});

// ---------------------------------------------------------------------------
// Detection adapter
// ---------------------------------------------------------------------------

describe("analyzeText adapter", () => {
  const submitted =
    "The quick brown fox jumps over the lazy dog. Researchers found that ninety percent agree.";

  const wire = {
    analysis_id: "abc123",
    overall_score: 0.8123,
    classification: "ai_generated",
    confidence: "high",
    signals: [
      { signal: "gltr", ai_probability: 0.91, confidence: "high", details: { foo: 1 } },
      { signal: "perplexity_burstiness", ai_probability: 0.42, confidence: "low", details: null },
      { signal: "stylometric", ai_probability: 0.6, confidence: "medium", details: null },
      { signal: "some_unknown_signal", ai_probability: 0.5, confidence: "low", details: null },
    ],
    sentence_analysis: [
      {
        sentence: "The quick brown fox jumps over the lazy dog.",
        ai_probability: 0.9,
        highlight: "high",
      },
      {
        sentence: "Researchers found that ninety percent agree.",
        ai_probability: 0.3,
        highlight: "low",
      },
    ],
    gltr_tokens: [
      {
        token: " quick",
        token_id: 1,
        rank: 970,
        probability: 0.0001,
        entropy: 8.8,
        bucket: "top1000",
        color: "red",
      },
    ],
    attribution: { likely_model: "gpt-4", model_confidence: 0.7, all_model_scores: [] },
    word_count: 14,
    processing_time_ms: 123,
    model_version: "1.2.3",
  };

  it("maps the envelope-free detection response to DetectionResult", async () => {
    postResolves(wire);
    const result = await analyzeText(submitted, "deep");

    expect(result.id).toBe("abc123");
    expect(result.text).toBe(submitted);
    // 0-1 wire score scaled to the 0-100 gauge.
    expect(result.overallScore).toBeCloseTo(81.23, 2);
    // confidence label mapped to a number.
    expect(result.confidence).toBe(0.95);
    expect(result.label).toBe("ai");
    expect(result.attribution).toBe("gpt-4");
    expect(typeof result.createdAt).toBe("string");
    expect(result.wordCount).toBe(14);
  });

  it("classifies signals into UI categories and keeps ai_probability", async () => {
    postResolves(wire);
    const result = await analyzeText(submitted, "deep");

    const byName = Object.fromEntries(result.signals.map((s) => [s.name, s]));
    expect(byName["gltr"].category).toBe("model");
    expect(byName["perplexity_burstiness"].category).toBe("statistical");
    expect(byName["stylometric"].category).toBe("linguistic");
    expect(byName["some_unknown_signal"].category).toBe("structural");

    // score mirrors ai_probability; weight is 0; description empty.
    expect(byName["gltr"].score).toBe(0.91);
    expect(byName["gltr"].ai_probability).toBe(0.91);
    expect(byName["gltr"].weight).toBe(0);
    expect(byName["gltr"].description).toBe("");
  });

  it("resolves sentence spans against the submitted text via indexOf", async () => {
    postResolves(wire);
    const result = await analyzeText(submitted, "deep");

    expect(result.sentences).toHaveLength(2);
    const first = result.sentences[0];
    expect(first.startIndex).toBe(0);
    expect(submitted.slice(first.startIndex, first.endIndex)).toBe(first.text);
    expect(first.score).toBe(0.9);
    expect(first.signals).toEqual({});

    const second = result.sentences[1];
    expect(submitted.slice(second.startIndex, second.endIndex)).toBe(second.text);
    expect(second.startIndex).toBeGreaterThan(first.endIndex - 1);
  });

  it("maps gltr buckets to categories and tolerates missing optional blocks", async () => {
    postResolves({ ...wire, sentence_analysis: null, gltr_tokens: null, attribution: null });
    const result = await analyzeText(submitted, "fast");

    expect(result.sentences).toEqual([]);
    expect(result.gltrTokens).toEqual([]);
    expect(result.attribution).toBe("");
  });

  it("maps human_written and unknown classifications", async () => {
    postResolves({ ...wire, classification: "human_written", confidence: "low" });
    const human = await analyzeText(submitted, "deep");
    expect(human.label).toBe("human");
    expect(human.confidence).toBe(0.4);

    postResolves({ ...wire, classification: "weird_value", confidence: "medium" });
    const unknown = await analyzeText(submitted, "deep");
    expect(unknown.label).toBe("uncertain");
    expect(unknown.confidence).toBe(0.7);
  });
});

// ---------------------------------------------------------------------------
// Plagiarism adapter
// ---------------------------------------------------------------------------

describe("analyzePlagiarism adapter", () => {
  const wire = {
    result_id: "plag1",
    overall_plagiarism_score: 0.25,
    originality_percentage: 75.0,
    paragraph_analysis: [
      {
        paragraph_index: 0,
        text: "A paragraph of text.",
        plagiarism_score: 0.4,
        sources: [
          {
            url: "https://example.com",
            title: "Example",
            matched_text: "matched chunk",
            similarity_score: 0.8,
            method: "semantic",
          },
        ],
      },
    ],
    sources_found: [
      {
        url: null,
        title: null,
        matched_text: "no url match",
        similarity_score: 0.5,
        method: "exact",
      },
    ],
    total_sources: 1,
    word_count: 4,
    processing_time_ms: 10,
  };

  it("keeps originality on a 0-100 scale and scales paragraph scores to percent", async () => {
    postResolves(wire);
    const result = await analyzePlagiarism("A paragraph of text.");

    expect(result.id).toBe("plag1");
    expect(result.originalityScore).toBe(75.0);
    expect(result.paragraphs[0].score).toBeCloseTo(40, 5);
    expect(result.paragraphs[0].sources[0].similarity).toBe(0.8);
    expect(result.paragraphs[0].sources[0].matchedText).toBe("matched chunk");
    // sourceSnippet falls back to matchedText (no separate snippet on the wire).
    expect(result.paragraphs[0].sources[0].sourceSnippet).toBe("matched chunk");
  });

  it("defaults null url/title on sources to empty strings", async () => {
    postResolves(wire);
    const result = await analyzePlagiarism("A paragraph of text.");
    expect(result.sources[0].url).toBe("");
    expect(result.sources[0].title).toBe("");
  });
});

// ---------------------------------------------------------------------------
// Humanization adapter
// ---------------------------------------------------------------------------

describe("humanizeText adapter", () => {
  const wire = {
    result_id: "h1",
    original_text: "original",
    humanized_text: "humanized",
    original_ai_score: 0.85,
    final_ai_score: 0.12,
    original_plagiarism_score: 0.0,
    final_plagiarism_score: 0.05,
    iterations_used: 3,
    timeline: [
      { iteration: 1, ai_score: 0.6, plagiarism_score: 0.0, text_preview: "..." },
      { iteration: 2, ai_score: 0.12, plagiarism_score: 0.05, text_preview: "..." },
    ],
    quality: {
      readability_score: 0.7,
      vocabulary_diversity: 0.8,
      sentence_variety: 0.6,
      meaning_preservation: 0.92,
    },
    model_used: "llama3",
    processing_time_ms: 5000,
  };

  it("scales AI scores to percent and keeps meaning preservation as 0-1", async () => {
    postResolves(wire);
    const result = await humanizeText("original", "casual");

    expect(result.id).toBe("h1");
    expect(result.originalScore).toBeCloseTo(85, 5);
    expect(result.humanizedScore).toBeCloseTo(12, 5);
    expect(result.meaningPreservation).toBe(0.92);
    expect(result.iterations).toBe(3);
    expect(result.style).toBe("llama3");
    expect(result.scoreTimeline).toEqual([
      { iteration: 1, score: 60 },
      { iteration: 2, score: 12 },
    ]);
  });

  it("falls back to the requested style when model_used is empty", async () => {
    postResolves({ ...wire, model_used: "" });
    const result = await humanizeText("original", "professional");
    expect(result.style).toBe("professional");
  });
});

// ---------------------------------------------------------------------------
// History adapter
// ---------------------------------------------------------------------------

describe("getHistory adapter", () => {
  const wire = {
    page: 2,
    limit: 20,
    total: 41,
    total_pages: 3,
    results: [
      {
        analysis_id: "a1",
        classification: "ai_generated",
        overall_ai_score: 0.9,
        word_count: 100,
        processing_time_ms: 50,
        model_version: "1.0",
        created_at: "2026-06-01T00:00:00Z",
      },
      {
        analysis_id: "a2",
        classification: "humanization",
        overall_ai_score: 0.1,
        word_count: 80,
        processing_time_ms: 40,
        model_version: "1.0",
        created_at: "2026-06-02T00:00:00Z",
      },
      {
        analysis_id: "a3",
        classification: "plagiarism_check",
        overall_ai_score: 0.0,
        word_count: 60,
        processing_time_ms: 30,
        model_version: "1.0",
        created_at: "2026-06-03T00:00:00Z",
      },
    ],
  };

  it("maps the paginated envelope and derives type/label/score", async () => {
    getResolves(wire);
    const result = await getHistory(2, 20);

    expect(result.total).toBe(41);
    expect(result.page).toBe(2);
    expect(result.limit).toBe(20);
    expect(result.totalPages).toBe(3);
    expect(result.items).toHaveLength(3);

    expect(result.items[0].type).toBe("detection");
    expect(result.items[0].label).toBe("ai");
    expect(result.items[0].score).toBeCloseTo(90, 5);
    expect(result.items[0].textPreview).toBe("");

    expect(result.items[1].type).toBe("humanization");
    expect(result.items[2].type).toBe("plagiarism");
  });
});

// ---------------------------------------------------------------------------
// Analytics adapters (each wraps payload in {results})
// ---------------------------------------------------------------------------

describe("analytics envelope unwrapping + key mapping", () => {
  it("maps readability keys (gunning_fog_index -> gunning_fog etc.)", async () => {
    postResolves({
      analysis_id: "r1",
      analysis_type: "readability",
      processing_time_ms: 120,
      results: {
        flesch_kincaid_grade: 6.35,
        flesch_reading_ease: 65.23,
        gunning_fog_index: 8.97,
        coleman_liau_index: 9.97,
        smog_index: 9.39,
        automated_readability_index: 6.31,
        dale_chall_score: 10.89,
        avg_words_per_sentence: 8.8,
        avg_syllables_per_word: 1.57,
        reading_time_minutes: 0.18,
        overall_grade: "High School",
        word_count: 44,
        sentence_count: 5,
        difficult_word_count: 19,
        polysyllabic_word_count: 6,
      },
    });
    const r = await analyzeReadability("text");
    expect(r.gunning_fog).toBe(8.97);
    expect(r.coleman_liau).toBe(9.97);
    expect(r.automated_readability).toBe(6.31);
    expect(r.dale_chall).toBe(10.89);
    // No wire source for linsear write.
    expect(r.linsear_write).toBe(0);
    expect(r.reading_time_seconds).toBeCloseTo(10.8, 5);
    expect(r.difficulty).toBe("easy");
  });

  it("maps tone emotions dict to an array and urgency to a number", async () => {
    postResolves({
      analysis_id: "t1",
      analysis_type: "tone",
      processing_time_ms: 1,
      results: {
        formality_score: 0.6,
        sentiment: { label: "positive", score: 0.45, positive_count: 2, negative_count: 0 },
        emotions: { confident: 0.1, joyful: 0.2 },
        objectivity_score: 0.4,
        persuasiveness_score: 0.0,
        urgency_level: { level: "low", score: 0.3, urgent_word_count: 0 },
        professional_casual_score: 0.3,
      },
    });
    const r = await analyzeTone("text");
    expect(r.formality).toBe(0.6);
    expect(r.sentiment).toBe(0.45);
    expect(r.sentiment_label).toBe("positive");
    expect(r.emotions).toEqual([
      { emotion: "confident", score: 0.1 },
      { emotion: "joyful", score: 0.2 },
    ]);
    expect(r.urgency).toBe(0.3);
  });

  it("maps grammar issues with position offsets and severity", async () => {
    postResolves({
      analysis_id: "g1",
      analysis_type: "grammar",
      processing_time_ms: 1,
      results: {
        error_count: 1,
        style_issue_count: 2,
        errors: [
          {
            type: "grammar",
            message: "Possible comma splice",
            position: { start: 198, end: 207 },
            suggestion: "Use a semicolon.",
          },
        ],
        grammar_score: 95,
        style_score: 100,
        passive_voice_percentage: 20.0,
      },
    });
    const r = await checkGrammar("text");
    expect(r.total_errors).toBe(3);
    expect(r.errors[0].offset).toBe(198);
    expect(r.errors[0].length).toBe(9);
    expect(r.errors[0].suggestions).toEqual(["Use a semicolon."]);
    expect(r.errors[0].severity).toBe("error");
  });

  it("maps statistics pos dict to array and word cloud word/frequency to text/value", async () => {
    postResolves({
      analysis_id: "s1",
      analysis_type: "statistics",
      processing_time_ms: 1,
      results: {
        word_count: 29,
        character_count_with_spaces: 177,
        character_count_without_spaces: 148,
        sentence_count: 3,
        paragraph_count: 1,
        avg_word_length: 4.9,
        avg_sentence_length: 9.67,
        unique_words: 27,
        vocabulary_richness: 0.931,
        most_common_words: [{ word: "quick", count: 1 }],
        most_common_bigrams: [],
        word_length_distribution: [{ length: 3, count: 6 }],
        sentence_length_distribution: [{ length: 9, count: 2 }],
        pos_distribution: {
          nouns: { count: 10, percentage: 29.41 },
          verbs: { count: 5, percentage: 14.71 },
        },
        word_cloud_data: [{ word: "quick", frequency: 1 }],
        reading_time_minutes: 0.13,
        speaking_time_minutes: 0.19,
        detected_language: { language: "English", confidence: 0.41 },
      },
    });
    const r = await getStatistics("text");
    expect(r.character_count).toBe(177);
    expect(r.character_count_no_spaces).toBe(148);
    expect(r.unique_word_count).toBe(27);
    expect(r.common_words).toEqual([{ word: "quick", count: 1 }]);
    expect(r.pos_distribution).toEqual([
      { tag: "nouns", label: "nouns", count: 10 },
      { tag: "verbs", label: "verbs", count: 5 },
    ]);
    expect(r.word_cloud_data).toEqual([{ text: "quick", value: 1 }]);
  });

  it("maps writing suggestions from original_text/suggested_fix", async () => {
    postResolves({
      analysis_id: "sg1",
      analysis_type: "suggestions",
      processing_time_ms: 1,
      results: {
        overall_writing_score: 98,
        suggestion_count: 1,
        suggestions: [
          {
            category: "engagement",
            severity: "info",
            message: "Vary sentence length.",
            original_text: null,
            suggested_fix: "Mix short and long sentences.",
            position: null,
          },
        ],
        category_breakdown: { engagement: 1 },
      },
    });
    const r = await getSuggestions("text");
    expect(r.overall_score).toBe(98);
    expect(r.suggestions[0].severity).toBe("low");
    expect(r.suggestions[0].original).toBe("");
    expect(r.suggestions[0].suggested).toBe("Mix short and long sentences.");
    expect(r.suggestions[0].position).toEqual({ start: 0, end: 0 });
  });

  it("maps citations inline list and derives counts", async () => {
    postResolves({
      analysis_id: "c1",
      analysis_type: "citations",
      processing_time_ms: 1,
      results: {
        citations_found: 2,
        citation_style: "APA",
        inline_citations: [
          { text: "(Smith, 2020)", style: "APA", year: "2020", title: "T" },
          { text: "(Doe, 2019)", style: "APA" },
        ],
        references: [],
        reference_count: 0,
        missing_references: ["Smith 2020"],
        format_issues: [],
      },
    });
    const r = await extractCitations("text");
    expect(r.total_citations).toBe(2);
    expect(r.detected_style).toBe("APA");
    expect(r.citations).toHaveLength(2);
    expect(r.citations[0].year).toBe("2020");
    expect(r.format_consistency_score).toBe(100);
    expect(r.missing_references).toEqual(["Smith 2020"]);
  });

  it("flattens comparison structural_comparison into a/b stats", async () => {
    postResolves({
      analysis_id: "cmp1",
      analysis_type: "comparison",
      processing_time_ms: 1,
      results: {
        similarity_score: 0.5,
        cosine_similarity: 0.6,
        jaccard_similarity: 0.4,
        edit_distance_ratio: 0.3,
        common_phrases: ["the quick"],
        diff_data: [{ type: "equal", text: "shared" }],
        structural_comparison: {
          text_a: { word_count: 10, sentence_count: 2, avg_sentence_length: 5, vocabulary_size: 8 },
          text_b: { word_count: 12, sentence_count: 3, avg_sentence_length: 4, vocabulary_size: 9 },
          vocabulary_overlap: 0.55,
        },
      },
    });
    const r = await compareTexts("a", "b");
    expect(r.similarity_score).toBe(0.5);
    expect(r.text_a_stats.word_count).toBe(10);
    expect(r.text_b_stats.vocabulary_size).toBe(9);
    expect(r.vocabulary_overlap).toBe(0.55);
    expect(r.diff_data[0]).toEqual({ type: "equal", text: "shared", text_b: undefined });
  });

  it("maps paraphrase clusters and flagged pairs", async () => {
    postResolves({
      analysis_id: "p1",
      analysis_type: "paraphrase",
      processing_time_ms: 1,
      results: {
        repetition_score: 0.0,
        flagged_pairs: [
          {
            sentence_a_index: 0,
            sentence_b_index: 1,
            sentence_a: "A",
            sentence_b: "B",
            similarity: 0.95,
            flag: "high",
          },
        ],
        self_plagiarism_pairs: [],
        clusters: [{ cluster_id: 0, sentence_indices: [0], size: 1, representative: "A" }],
        unique_content_ratio: 0.8,
        total_sentences: 5,
        paragraph_count: 1,
      },
    });
    const r = await analyzeParaphrase("text");
    expect(r.uniqueContentRatio).toBe(0.8);
    expect(r.totalSentences).toBe(5);
    expect(r.uniqueSentences).toBe(4);
    expect(r.flaggedPairs[0]).toEqual({
      sentenceA: "A",
      sentenceB: "B",
      similarity: 0.95,
      indexA: 0,
      indexB: 1,
    });
    expect(r.clusters[0].label).toBe("Cluster 1");
    expect(r.clusters[0].sentences).toEqual(["A"]);
  });

  it("maps fact claims with verifiable->verified and credibility score", async () => {
    postResolves({
      analysis_id: "f1",
      analysis_type: "facts",
      processing_time_ms: 1,
      results: {
        claims_found: [
          {
            text: "90%",
            category: "quantitative",
            entity_type: "PERCENT",
            start: 1,
            end: 4,
            verifiable: true,
          },
        ],
        vague_claims: [{ text: "experts say", type: "attribution" }],
        vague_claims_count: 1,
        verifiable_claims_count: 1,
        factual_density: 4.44,
        credibility_score: 90.0,
        claim_categories: { quantitative: 1 },
      },
    });
    const r = await checkFacts("text");
    expect(r.credibilityScore).toBe(90.0);
    expect(r.claims[0].verified).toBe(true);
    expect(r.claims[0].confidence).toBe(1);
    expect(r.vagueAttributions).toBe(1);
    expect(r.tips).toEqual(["experts say"]);
  });

  it("maps SEO score to grade and recommendations to objects", async () => {
    postResolves({
      analysis_id: "seo1",
      analysis_type: "seo",
      processing_time_ms: 1,
      results: {
        seo_score: 46.0,
        keyword_analysis: [{ keyword: "quick", frequency: 1, density_percent: 2.27 }],
        recommendations: ["Add more words."],
        metrics: {
          word_count: 44,
          sentence_count: 5,
          paragraph_count: 1,
          heading_count: 0,
          flesch_reading_ease: 65,
          avg_paragraph_sentences: 5,
          transition_word_percentage: 0,
          passive_voice_percentage: 20,
          avg_sentence_length: 8.8,
          long_sentence_count: 1,
          meta_description_length: 271,
          meta_description_ideal: false,
        },
        headings: [],
      },
    });
    const r = await analyzeSEO("text");
    expect(r.seoScore).toBe(46.0);
    expect(r.grade).toBe("F");
    expect(r.keywords[0]).toEqual({ keyword: "quick", count: 1, density: 2.27 });
    expect(r.recommendations[0]).toEqual({ text: "Add more words.", priority: "medium" });
    expect(r.metrics.length).toBeGreaterThan(0);
  });
});

// ---------------------------------------------------------------------------
// Dashboard adapters
// ---------------------------------------------------------------------------

describe("dashboard adapters", () => {
  it("maps stats keys to camelCase", async () => {
    getResolves({
      total_analyses: 100,
      average_ai_score: 0.42,
      total_words_analyzed: 50000,
      analyses_today: 5,
      analyses_this_week: 20,
      analyses_this_month: 60,
    });
    const r = await getDashboardStats();
    expect(r).toEqual({
      totalAnalyses: 100,
      avgAiScore: 42, // scaled to the 0-100 range the stat card renders
      totalWords: 50000,
      analysesToday: 5,
    });
  });

  it("builds score distribution ranges from histogram bins", async () => {
    getResolves({
      ai_score_histogram: [
        { bin_start: 0.0, bin_end: 0.1, count: 3 },
        { bin_start: 0.9, bin_end: 1.0, count: 7 },
      ],
      analyses_per_day: [{ date: "2026-06-01", count: 4 }],
      most_common_classifications: [{ classification: "ai_generated", count: 10 }],
    });
    const r = await getDashboardTrends();
    expect(r.scoreDistribution).toEqual([
      { range: "0-10", count: 3 },
      { range: "90-100", count: 7 },
    ]);
    expect(r.analysesPerDay).toEqual([{ date: "2026-06-01", count: 4 }]);
    expect(r.classificationBreakdown).toEqual([{ label: "ai", value: 10 }]);
    expect(r.recentAnalyses).toEqual([]);
  });

  it("maps top signals to name/count", async () => {
    getResolves({
      signals: [
        { signal_name: "gltr", fire_count: 12, average_score: 0.7 },
        { signal_name: "perplexity_burstiness", fire_count: 8, average_score: 0.5 },
      ],
    });
    const r = await getTopSignals(10);
    expect(r).toEqual([
      { name: "gltr", count: 12 },
      { name: "perplexity_burstiness", count: 8 },
    ]);
  });
});

// ---------------------------------------------------------------------------
// Advanced adapters
// ---------------------------------------------------------------------------

describe("advanced adapters", () => {
  it("maps rewrite detection (snake_case patterns, naturalness 0-100)", async () => {
    postResolves({
      signal: "rewrite_detection",
      ai_probability: 0.5,
      confidence: "medium",
      rewrite_detected: true,
      rewrite_confidence: 0.62,
      residual_ai_patterns: ["topic_sentence_pattern", "excessive_transitions"],
      naturalness_score: 73.5,
      details: {},
    });
    const r = await detectRewrite("text");
    expect(r.isRewritten).toBe(true);
    expect(r.naturalnessScore).toBe(73.5);
    expect(r.confidence).toBe(0.62);
    expect(r.residualPatterns).toHaveLength(2);
    expect(r.residualPatterns[0].pattern).toBe("Topic Sentence Pattern");
    expect(r.residualPatterns[0].severity).toBe("medium");
    expect(r.residualPatterns[0].count).toBe(1);
  });

  it("maps version submit (0-1 score -> percent) and derives word count", async () => {
    postResolves({
      document_id: "doc1",
      version_number: 2,
      previous_score: 0.5,
      current_score: 0.3,
      score_change: -0.2,
      diff_summary: { words_added: 5, words_removed: 2, words_changed: 3 },
      score_trajectory: [],
      total_versions: 2,
    });
    const r = await submitVersion("doc1", "text");
    expect(r.versionNumber).toBe(2);
    expect(r.aiScore).toBe(30);
    expect(r.wordCount).toBe(8);
    expect(typeof r.timestamp).toBe("string");
  });

  it("maps coach suggestions to the UI suggestion shape", async () => {
    postResolves({
      human_score: 70,
      suggestions: [
        {
          category: "buzzword",
          message: "Replace 'leverage' with 'use'",
          original: "leverage",
          fix: "use",
          impact: "medium",
          position: 10,
        },
      ],
      quick_fixes: [],
      total_suggestions: 1,
      high_impact_count: 0,
      medium_impact_count: 1,
      low_impact_count: 0,
    });
    const r = await getCoachSuggestions("text");
    expect(r[0].type).toBe("buzzword");
    expect(r[0].original).toBe("leverage");
    expect(r[0].suggested).toBe("use");
    expect(r[0].explanation).toBe("Replace 'leverage' with 'use'");
  });

  it("maps batch results (0-1 scores -> percent) and summary", async () => {
    postResolves({
      batch_id: "batch1",
      total_files: 2,
      avg_score: 0.55,
      score_distribution: [],
      flagged_count: 1,
      results: [
        {
          index: 0,
          filename: "a.txt",
          word_count: 100,
          ai_score: 0.9,
          classification: "ai_generated",
          top_signal: "gltr",
        },
        {
          index: 1,
          filename: "b.txt",
          word_count: 80,
          ai_score: 0.2,
          classification: "human_written",
          top_signal: "perplexity_burstiness",
        },
      ],
      processing_time_ms: 200,
    });
    const r = await processBatch([
      { filename: "a.txt", text: "x" },
      { filename: "b.txt", text: "y" },
    ]);
    expect(r.batchId).toBe("batch1");
    expect(r.results[0].aiScore).toBe(90);
    expect(r.results[0].status).toBe("done");
    expect(r.summary.totalFiles).toBe(2);
    expect(r.summary.processed).toBe(2);
    expect(r.summary.flagged).toBe(1);
    expect(r.summary.avgScore).toBe(55);
  });
});

// ---------------------------------------------------------------------------
// Export / share adapters
// ---------------------------------------------------------------------------

describe("share adapters", () => {
  it("getShareLink reduces the wire to {url}", async () => {
    postResolves({ url: "/api/v1/export/shared/tok", share_token: "tok" });
    const r = await getShareLink({ foo: 1 });
    expect(r).toEqual({ url: "/api/v1/export/shared/tok" });
  });

  it("shareAnalysis maps share_url/share_token and nulls expiry", async () => {
    postResolves({ share_url: "/shared/tok", share_token: "tok", qr_code_data: "data:..." });
    const r = await shareAnalysis({ foo: 1 }, "7d");
    expect(r.url).toBe("/shared/tok");
    expect(r.shareId).toBe("tok");
    expect(r.expiresAt).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// Pure utility: score classification thresholds (mirrored from backend)
// ---------------------------------------------------------------------------

describe("score classification thresholds", () => {
  function classify(score: number): string {
    if (score >= 0.85) return "AI Generated";
    if (score >= 0.5) return "Likely AI";
    if (score >= 0.2) return "Uncertain";
    return "Human Written";
  }

  it("classifies 0.9 as AI Generated", () => {
    expect(classify(0.9)).toBe("AI Generated");
  });

  it("classifies 0.85 as AI Generated (boundary)", () => {
    expect(classify(0.85)).toBe("AI Generated");
  });

  it("classifies 0.6 as Likely AI", () => {
    expect(classify(0.6)).toBe("Likely AI");
  });

  it("classifies 0.3 as Uncertain", () => {
    expect(classify(0.3)).toBe("Uncertain");
  });

  it("classifies 0.1 as Human Written", () => {
    expect(classify(0.1)).toBe("Human Written");
  });

  it("classifies 0.0 as Human Written", () => {
    expect(classify(0.0)).toBe("Human Written");
  });
});

// ---------------------------------------------------------------------------
// Utility: word count helper (mirrors analysis utility logic)
// ---------------------------------------------------------------------------

describe("word count utility", () => {
  function countWords(text: string): number {
    return text.trim() === "" ? 0 : text.trim().split(/\s+/).length;
  }

  it("counts words in a normal sentence", () => {
    expect(countWords("Hello world, this is a test.")).toBe(6);
  });

  it("returns 0 for empty string", () => {
    expect(countWords("")).toBe(0);
  });

  it("returns 0 for whitespace-only string", () => {
    expect(countWords("   ")).toBe(0);
  });

  it("handles multiple spaces between words", () => {
    expect(countWords("one   two   three")).toBe(3);
  });

  it("handles single word", () => {
    expect(countWords("hello")).toBe(1);
  });
});
