/**
 * Accessibility checks for each page.
 *
 * Every page is rendered inside its providers and scanned with axe-core via
 * vitest-axe. The api module is mocked so nothing hits the network. Pages with
 * genuine, pre-existing violations are not patched here (that would mean
 * editing source components); instead the gap is documented with test.todo and
 * reported. The matcher is extended locally so the shared test setup is left
 * untouched.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { axe } from "vitest-axe";
import * as matchers from "vitest-axe/matchers";
import type { AxeMatchers } from "vitest-axe/matchers";
import { renderWithProviders } from "./helpers/providers";

// Teach vitest's expect about the axe matcher. vitest 1.x resolves custom
// matcher types through @vitest/expect's Assertion interface, so augment that.
declare module "@vitest/expect" {
  // eslint-disable-next-line @typescript-eslint/no-empty-object-type
  interface Assertion extends AxeMatchers {}
  // eslint-disable-next-line @typescript-eslint/no-empty-object-type
  interface AsymmetricMatchersContaining extends AxeMatchers {}
}

expect.extend(matchers);

vi.mock("@/utils/api");
import * as api from "@/utils/api";

import PlagiarismPage from "@/pages/PlagiarismPage";
import HumanizePage from "@/pages/HumanizePage";
import AnalyticsPage from "@/pages/AnalyticsPage";
import BatchPage from "@/pages/BatchPage";
import DetectPage from "@/pages/DetectPage";
import ComparePage from "@/pages/ComparePage";
import HistoryPage from "@/pages/HistoryPage";
import DashboardPage from "@/pages/DashboardPage";

const mockedApi = vi.mocked(api);

beforeEach(() => {
  vi.clearAllMocks();
  mockedApi.getHistory.mockResolvedValue({
    items: [],
    total: 0,
    page: 1,
    limit: 20,
    totalPages: 0,
  });
});

describe("page accessibility — clean pages", () => {
  it("PlagiarismPage has no axe violations", async () => {
    const { container } = renderWithProviders(<PlagiarismPage />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it("HumanizePage has no axe violations", async () => {
    const { container } = renderWithProviders(<HumanizePage />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it("AnalyticsPage has no axe violations", async () => {
    const { container } = renderWithProviders(<AnalyticsPage />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it("BatchPage has no axe violations", async () => {
    const { container } = renderWithProviders(<BatchPage />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});

/**
 * These four pages had real violations when the suite was first written:
 * skipped heading levels on Detect/Compare, an unnamed filter combobox on
 * History, an unnamed loading progressbar on Dashboard. The components were
 * fixed (semantic heading components, labelId wiring, an aria-label), so
 * they are asserted clean like the rest.
 */
describe("page accessibility — previously violating pages", () => {
  it("DetectPage has no axe violations", async () => {
    const { container } = renderWithProviders(<DetectPage />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it("ComparePage has no axe violations", async () => {
    const { container } = renderWithProviders(<ComparePage />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it("HistoryPage has no axe violations", async () => {
    const { container } = renderWithProviders(<HistoryPage />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it("DashboardPage has no axe violations", async () => {
    const { container } = renderWithProviders(<DashboardPage />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
