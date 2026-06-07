/**
 * Console hygiene for page renders.
 *
 * Each page is mounted, allowed to settle, and unmounted while a spy records
 * everything that reaches console.error. Known test-harness noise is filtered
 * out (React's act() warnings, which come from async state settling and
 * framer-motion animations under jsdom, and jsdom's "Not implemented:
 * navigation" notice). Anything left is a genuine error the page logged on its
 * own, and the test fails on it rather than hiding it.
 *
 * As of writing, no page produces an unfiltered console.error — the only
 * output during renders is act() warnings and the jsdom navigation notice.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { act } from "@testing-library/react";
import { renderWithProviders } from "./helpers/providers";

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

// Substrings that mark expected, non-actionable harness noise.
const IGNORED = [
  "not wrapped in act",
  "inside a test was not wrapped in act",
  "Not implemented: navigation",
];

function isIgnored(args: unknown[]): boolean {
  const text = args.map((a) => (a instanceof Error ? a.message : String(a))).join(" ");
  return IGNORED.some((needle) => text.includes(needle));
}

let originalError: typeof console.error;
let unexpected: unknown[][];

beforeEach(() => {
  vi.clearAllMocks();
  unexpected = [];
  originalError = console.error;
  console.error = (...args: unknown[]) => {
    if (!isIgnored(args)) unexpected.push(args);
  };

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

afterEach(() => {
  console.error = originalError;
});

async function renderAndSettle(ui: React.ReactElement) {
  const utils = renderWithProviders(ui);
  // Let any mount-time effects/queries flush.
  await act(async () => {
    await Promise.resolve();
  });
  utils.unmount();
}

const pages: [string, React.ReactElement][] = [
  ["DetectPage", <DetectPage />],
  ["PlagiarismPage", <PlagiarismPage />],
  ["HumanizePage", <HumanizePage />],
  ["HistoryPage", <HistoryPage />],
  ["AnalyticsPage", <AnalyticsPage />],
  ["ComparePage", <ComparePage />],
  ["DashboardPage", <DashboardPage />],
  ["BatchPage", <BatchPage />],
];

describe("page render console hygiene", () => {
  it.each(pages)("%s logs no unexpected console.error", async (_name, ui) => {
    await renderAndSettle(ui);
    expect(unexpected).toEqual([]);
  });
});
