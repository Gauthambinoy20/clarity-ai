/**
 * Smoke and interaction tests for the eight top-level pages.
 *
 * Every page is rendered inside the theme + router + query providers it expects.
 * The api module is fully mocked so nothing reaches the network; default mocks
 * resolve to empty-ish payloads so the initial (empty/loading) states render.
 * Individual tests override a mock to drive success and error paths.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { DetectionResult } from "@/types/analysis";
import { renderWithProviders } from "./helpers/providers";
import { useAppStore } from "@/stores/appStore";

vi.mock("@/utils/api");
import * as api from "@/utils/api";

import DetectPage from "@/pages/DetectPage";
import PlagiarismPage from "@/pages/PlagiarismPage";
import HumanizePage from "@/pages/HumanizePage";
import HistoryPage from "@/pages/HistoryPage";
import AnalyticsPage from "@/pages/AnalyticsPage";
import ComparePage from "@/pages/ComparePage";
import DashboardPage from "@/pages/DashboardPage";
import BatchPage from "@/pages/BatchPage";

const mockedApi = vi.mocked(api);

const detectionFixture: DetectionResult = {
  id: "det-1",
  text: "A longer block of analyzed text used for the result region.",
  overallScore: 73,
  confidence: 0.84,
  label: "ai",
  signals: [
    {
      name: "perplexity",
      signal: "perplexity",
      score: 0.8,
      ai_probability: 0.8,
      weight: 1,
      description: "predictability",
      category: "statistical",
    },
  ],
  sentences: [],
  gltrTokens: [],
  attribution: "gpt-4",
  wordCount: 60,
  processingTimeMs: 700,
  createdAt: "2024-01-01T00:00:00Z",
};

beforeEach(() => {
  vi.clearAllMocks();
  useAppStore.setState({
    detectionResult: null,
    plagiarismResult: null,
    humanizationResult: null,
    isAnalyzing: false,
    history: [],
  });
  // Sensible defaults so pages that auto-fetch on mount resolve cleanly.
  mockedApi.getHistory.mockResolvedValue({
    items: [],
    total: 0,
    page: 1,
    limit: 20,
    totalPages: 0,
  });
  mockedApi.getDashboardStats.mockResolvedValue({
    totalAnalyses: 0,
    avgAiScore: 0,
    totalWords: 0,
    analysesToday: 0,
  });
  mockedApi.getDashboardTrends.mockResolvedValue({
    scoreDistribution: [],
    analysesPerDay: [],
    classificationBreakdown: [],
    recentAnalyses: [],
  });
  mockedApi.getTopSignals.mockResolvedValue([]);
});

// ---------------------------------------------------------------------------
// Every page mounts without throwing
// ---------------------------------------------------------------------------

describe("page smoke renders", () => {
  it("renders DetectPage", () => {
    renderWithProviders(<DetectPage />);
    expect(screen.getByText("AI Content Detection")).toBeInTheDocument();
  });

  it("renders PlagiarismPage", () => {
    renderWithProviders(<PlagiarismPage />);
    expect(screen.getByText("Plagiarism Detection")).toBeInTheDocument();
  });

  it("renders HumanizePage", () => {
    renderWithProviders(<HumanizePage />);
    // Page mounts; an analyze control is present.
    expect(screen.getAllByRole("button").length).toBeGreaterThan(0);
  });

  it("renders HistoryPage", () => {
    renderWithProviders(<HistoryPage />);
    expect(screen.getByText("Analysis History")).toBeInTheDocument();
  });

  it("renders AnalyticsPage", () => {
    renderWithProviders(<AnalyticsPage />);
    expect(screen.getByText("Text Analytics")).toBeInTheDocument();
  });

  it("renders ComparePage", () => {
    renderWithProviders(<ComparePage />);
    expect(screen.getAllByRole("button").length).toBeGreaterThan(0);
  });

  it("renders DashboardPage", () => {
    renderWithProviders(<DashboardPage />);
    expect(mockedApi.getDashboardStats).toHaveBeenCalled();
  });

  it("renders BatchPage", () => {
    renderWithProviders(<BatchPage />);
    expect(screen.getAllByRole("button").length).toBeGreaterThan(0);
  });
});

// ---------------------------------------------------------------------------
// DetectPage: full happy/error/loading interaction
// ---------------------------------------------------------------------------

describe("DetectPage detection flow", () => {
  it("shows the empty dashboard before any analysis", () => {
    renderWithProviders(<DetectPage />);
    expect(screen.getByText("Analysis Dashboard")).toBeInTheDocument();
  });

  it("submits typed text and calls the detection API with the input", async () => {
    const user = userEvent.setup();
    mockedApi.analyzeText.mockResolvedValue(detectionFixture);

    renderWithProviders(<DetectPage />);

    // The submit button needs at least 50 words to enable.
    const longText = Array(60).fill("word").join(" ");
    const textbox = screen.getByPlaceholderText(/Paste the text/i);
    await user.click(textbox);
    await user.paste(longText);

    const analyzeBtn = await screen.findByRole("button", { name: /analyze/i });
    await waitFor(() => expect(analyzeBtn).toBeEnabled());
    await user.click(analyzeBtn);

    // Successful submission calls the API and lands the result in the store.
    await waitFor(() =>
      expect(mockedApi.analyzeText).toHaveBeenCalledWith(longText, "deep", undefined)
    );
    await waitFor(() => expect(useAppStore.getState().detectionResult).toEqual(detectionFixture));
  });

  it("renders the result region when a detection result is present", () => {
    // Seed the store so the dashboard mounts directly (no exit transition,
    // which framer-motion's AnimatePresence does not settle under jsdom).
    useAppStore.setState({ detectionResult: detectionFixture, isAnalyzing: false });
    renderWithProviders(<DetectPage />);

    expect(screen.getByText("Detection Signals")).toBeInTheDocument();
    // The classification label is derived from the result label; it shows up
    // both on the chip and inside the score gauge.
    expect(screen.getAllByText("AI Generated").length).toBeGreaterThan(0);
    expect(screen.getByText("84% confident")).toBeInTheDocument();
  });

  it("renders the loading state while analyzing", () => {
    useAppStore.setState({ isAnalyzing: true });
    renderWithProviders(<DetectPage />);
    expect(screen.getByText(/Analyzing text across 16 signals/i)).toBeInTheDocument();
  });

  it("renders an error message when detection fails", async () => {
    const user = userEvent.setup();
    mockedApi.analyzeText.mockRejectedValue(new Error("server exploded"));

    renderWithProviders(<DetectPage />);

    const longText = Array(60).fill("word").join(" ");
    const textbox = screen.getByPlaceholderText(/Paste the text/i);
    await user.click(textbox);
    await user.paste(longText);

    const analyzeBtn = await screen.findByRole("button", { name: /analyze/i });
    await waitFor(() => expect(analyzeBtn).toBeEnabled());
    await user.click(analyzeBtn);

    expect(await screen.findByText("server exploded")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// AnalyticsPage primary states
// ---------------------------------------------------------------------------

describe("AnalyticsPage states", () => {
  it("disables the run button until the minimum word count is met (empty state)", () => {
    renderWithProviders(<AnalyticsPage />);
    const runBtn = screen.getByRole("button", { name: /run all analyses/i });
    expect(runBtn).toBeDisabled();
  });

  it("shows an error alert when the analytics request fails", async () => {
    const user = userEvent.setup();
    mockedApi.runFullAnalytics.mockRejectedValue(new Error("analytics down"));
    // Parallel side calls also reject harmlessly.
    mockedApi.analyzeParaphrase.mockRejectedValue(new Error("x"));
    mockedApi.checkFacts.mockRejectedValue(new Error("x"));
    mockedApi.analyzeSEO.mockRejectedValue(new Error("x"));

    renderWithProviders(<AnalyticsPage />);

    const longText = Array(60).fill("word").join(" ");
    const textbox = screen.getByPlaceholderText(/Paste or type text/i);
    await user.click(textbox);
    await user.paste(longText);

    const runBtn = screen.getByRole("button", { name: /run all analyses/i });
    await waitFor(() => expect(runBtn).toBeEnabled());
    await user.click(runBtn);

    expect(await screen.findByText("analytics down")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// PlagiarismPage primary states
// ---------------------------------------------------------------------------

describe("PlagiarismPage states", () => {
  it("renders the input prompt in its empty state", () => {
    renderWithProviders(<PlagiarismPage />);
    expect(screen.getByPlaceholderText(/check for plagiarism/i)).toBeInTheDocument();
  });

  it("shows the loading indicator while a check is running", () => {
    useAppStore.setState({ isAnalyzing: true });
    renderWithProviders(<PlagiarismPage />);
    // LoadingProgress renders a progressbar while analyzing.
    expect(screen.getByRole("progressbar")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// HistoryPage primary states
// ---------------------------------------------------------------------------

describe("HistoryPage states", () => {
  it("shows the empty-state row when there is no history", async () => {
    renderWithProviders(<HistoryPage />);
    expect(await screen.findByText("No analyses found.")).toBeInTheDocument();
  });

  it("renders fetched history rows", async () => {
    mockedApi.getHistory.mockResolvedValue({
      items: [
        {
          id: "h1",
          type: "detection",
          textPreview: "An earlier analysis preview",
          score: 64,
          label: "ai",
          createdAt: "2024-01-01T00:00:00Z",
        },
      ],
      total: 1,
      page: 1,
      limit: 20,
      totalPages: 1,
    });

    renderWithProviders(<HistoryPage />);
    expect(await screen.findByText("An earlier analysis preview")).toBeInTheDocument();
  });
});
