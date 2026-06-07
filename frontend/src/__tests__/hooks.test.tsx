/**
 * Tests for the react-query mutation hooks and the keyboard shortcut hook.
 *
 * The api module is the only thing mocked — every hook calls through it, so
 * mocking the network boundary lets us drive success, error, and loading
 * states without touching the hook logic itself.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import type { ReactNode } from "react";
import { renderHook, act, waitFor, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { DetectionResult, PlagiarismResult, HumanizationResult } from "@/types/analysis";
import type { ReadabilityResult } from "@/types/analytics";

vi.mock("@/utils/api");

import * as api from "@/utils/api";
import { useDetection } from "@/hooks/useDetection";
import { usePlagiarism } from "@/hooks/usePlagiarism";
import { useHumanization } from "@/hooks/useHumanization";
import { useReadability } from "@/hooks/useAnalytics";
import { useKeyboardShortcuts } from "@/hooks/useKeyboardShortcuts";
import { useAppStore } from "@/stores/appStore";

const mockedApi = vi.mocked(api);

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

// Realistic fixtures shaped from the real response types in src/types.
const detectionFixture: DetectionResult = {
  id: "det-1",
  text: "Sample analyzed text.",
  overallScore: 72,
  confidence: 0.81,
  label: "ai",
  signals: [],
  sentences: [],
  gltrTokens: [],
  attribution: "gpt-4",
  wordCount: 120,
  processingTimeMs: 850,
  createdAt: "2024-01-01T00:00:00Z",
};

const plagiarismFixture: PlagiarismResult = {
  id: "plag-1",
  text: "Some text to check.",
  originalityScore: 88,
  paragraphs: [],
  sources: [],
  createdAt: "2024-01-01T00:00:00Z",
};

const humanizationFixture: HumanizationResult = {
  id: "hum-1",
  originalText: "Robotic input text.",
  humanizedText: "A warmer rewrite of the input.",
  originalScore: 90,
  humanizedScore: 18,
  meaningPreservation: 0.96,
  style: "academic",
  iterations: 2,
  scoreTimeline: [
    { iteration: 0, score: 90 },
    { iteration: 1, score: 18 },
  ],
  createdAt: "2024-01-01T00:00:00Z",
};

const readabilityFixture: ReadabilityResult = {
  flesch_reading_ease: 60,
  flesch_kincaid_grade: 8,
  gunning_fog: 9,
  smog_index: 8,
  coleman_liau: 9,
  automated_readability: 8,
  dale_chall: 7,
  linsear_write: 8,
  overall_grade: "8th grade",
  reading_time_seconds: 30,
  reading_time_minutes: 0.5,
  difficulty: "moderate",
};

beforeEach(() => {
  vi.clearAllMocks();
  // Reset the slice of the store the hooks write into.
  useAppStore.setState({
    detectionResult: null,
    plagiarismResult: null,
    humanizationResult: null,
    isAnalyzing: false,
  });
});

describe("useDetection", () => {
  it("starts idle with no result", () => {
    const { result } = renderHook(() => useDetection(), { wrapper });
    expect(result.current.isIdle).toBe(true);
    expect(result.current.data).toBeUndefined();
  });

  it("calls analyzeText and stores the result on success", async () => {
    mockedApi.analyzeText.mockResolvedValue(detectionFixture);
    const { result } = renderHook(() => useDetection(), { wrapper });

    act(() => {
      result.current.mutate({ text: "Sample analyzed text." });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockedApi.analyzeText).toHaveBeenCalledWith("Sample analyzed text.", "deep", undefined);
    expect(result.current.data).toEqual(detectionFixture);
    expect(useAppStore.getState().detectionResult).toEqual(detectionFixture);
  });

  it("flips isAnalyzing on while the request is in flight", async () => {
    let resolve!: (value: DetectionResult) => void;
    mockedApi.analyzeText.mockReturnValue(
      new Promise<DetectionResult>((r) => {
        resolve = r;
      })
    );
    const { result } = renderHook(() => useDetection(), { wrapper });

    act(() => {
      result.current.mutate({ text: "pending text" });
    });

    await waitFor(() => expect(useAppStore.getState().isAnalyzing).toBe(true));
    expect(result.current.isPending).toBe(true);

    await act(async () => {
      resolve(detectionFixture);
    });
    await waitFor(() => expect(useAppStore.getState().isAnalyzing).toBe(false));
  });

  it("surfaces an error and clears the analyzing flag on failure", async () => {
    mockedApi.analyzeText.mockRejectedValue(new Error("detection boom"));
    const { result } = renderHook(() => useDetection(), { wrapper });

    act(() => {
      result.current.mutate({ text: "bad request" });
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error?.message).toBe("detection boom");
    expect(useAppStore.getState().isAnalyzing).toBe(false);
  });
});

describe("usePlagiarism", () => {
  it("stores the originality result on success", async () => {
    mockedApi.analyzePlagiarism.mockResolvedValue(plagiarismFixture);
    const { result } = renderHook(() => usePlagiarism(), { wrapper });

    act(() => {
      result.current.mutate({ text: "Some text to check." });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockedApi.analyzePlagiarism).toHaveBeenCalledWith("Some text to check.", undefined);
    expect(useAppStore.getState().plagiarismResult).toEqual(plagiarismFixture);
  });

  it("reports the API error message", async () => {
    mockedApi.analyzePlagiarism.mockRejectedValue(new Error("plagiarism boom"));
    const { result } = renderHook(() => usePlagiarism(), { wrapper });

    act(() => {
      result.current.mutate({ text: "x" });
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error?.message).toBe("plagiarism boom");
  });
});

describe("useHumanization", () => {
  it("stores the humanized result on success", async () => {
    mockedApi.humanizeText.mockResolvedValue(humanizationFixture);
    const { result } = renderHook(() => useHumanization(), { wrapper });

    act(() => {
      result.current.mutate({ text: "Robotic input text." });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockedApi.humanizeText).toHaveBeenCalledWith(
      "Robotic input text.",
      "academic",
      undefined
    );
    expect(useAppStore.getState().humanizationResult).toEqual(humanizationFixture);
  });

  it("reports the API error message", async () => {
    mockedApi.humanizeText.mockRejectedValue(new Error("humanize boom"));
    const { result } = renderHook(() => useHumanization(), { wrapper });

    act(() => {
      result.current.mutate({ text: "x" });
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error?.message).toBe("humanize boom");
  });
});

describe("useAnalytics (useReadability)", () => {
  it("is idle before being triggered", () => {
    const { result } = renderHook(() => useReadability(), { wrapper });
    expect(result.current.isIdle).toBe(true);
  });

  it("returns the readability payload on success", async () => {
    mockedApi.analyzeReadability.mockResolvedValue(readabilityFixture);
    const { result } = renderHook(() => useReadability(), { wrapper });

    act(() => {
      result.current.mutate("Some prose to analyze for readability.");
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockedApi.analyzeReadability).toHaveBeenCalledWith(
      "Some prose to analyze for readability."
    );
    expect(result.current.data).toEqual(readabilityFixture);
  });

  it("surfaces the error on failure", async () => {
    mockedApi.analyzeReadability.mockRejectedValue(new Error("analytics boom"));
    const { result } = renderHook(() => useReadability(), { wrapper });

    act(() => {
      result.current.mutate("x");
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error?.message).toBe("analytics boom");
  });
});

describe("useKeyboardShortcuts", () => {
  it("fires the matching handler on a plain key press", () => {
    const handler = vi.fn();
    renderHook(() => useKeyboardShortcuts([{ key: "k", handler }]));

    fireEvent.keyDown(window, { key: "k" });
    expect(handler).toHaveBeenCalledTimes(1);
  });

  it("respects the ctrl modifier", () => {
    const handler = vi.fn();
    renderHook(() => useKeyboardShortcuts([{ key: "Enter", ctrl: true, handler }]));

    // No modifier -> should not fire.
    fireEvent.keyDown(window, { key: "Enter" });
    expect(handler).not.toHaveBeenCalled();

    // With ctrl held -> fires.
    fireEvent.keyDown(window, { key: "Enter", ctrlKey: true });
    expect(handler).toHaveBeenCalledTimes(1);
  });

  it("does not fire handlers for unrelated keys", () => {
    const handler = vi.fn();
    renderHook(() => useKeyboardShortcuts([{ key: "a", handler }]));

    fireEvent.keyDown(window, { key: "b" });
    expect(handler).not.toHaveBeenCalled();
  });

  it("detaches the listener on unmount", () => {
    const handler = vi.fn();
    const { unmount } = renderHook(() => useKeyboardShortcuts([{ key: "z", handler }]));

    unmount();
    fireEvent.keyDown(window, { key: "z" });
    expect(handler).not.toHaveBeenCalled();
  });
});
