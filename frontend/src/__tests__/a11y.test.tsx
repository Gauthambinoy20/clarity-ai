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
  interface Assertion extends AxeMatchers {}
  interface AsymmetricMatchersContaining extends AxeMatchers {}
}

expect.extend(matchers);

vi.mock("@/utils/api");
import * as api from "@/utils/api";

import PlagiarismPage from "@/pages/PlagiarismPage";
import HumanizePage from "@/pages/HumanizePage";
import AnalyticsPage from "@/pages/AnalyticsPage";
import BatchPage from "@/pages/BatchPage";

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
 * Pages with real, pre-existing accessibility gaps. These are left as test.todo
 * rather than asserted, because making them pass would require editing the page
 * source (out of scope for this test work). Each todo names the exact axe rule
 * so the gap is unambiguous when someone picks it up.
 *
 * - DetectPage: "heading-order" (moderate) — a heading level is skipped; the
 *   first heading on the screen is an h4 with no preceding h1/h2/h3.
 * - ComparePage: "heading-order" (moderate) — same skipped-level issue.
 * - HistoryPage: "aria-input-field-name" (serious) — the "Type" filter Select
 *   exposes a combobox role with no accessible name to assistive tech.
 * - DashboardPage: "aria-progressbar-name" (serious) — a loading progressbar
 *   has no accessible name while data is being fetched.
 */
describe("page accessibility — known gaps", () => {
  it.todo("DetectPage: heading-order (h4 with no preceding higher-level heading)");
  it.todo("ComparePage: heading-order (h4 with no preceding higher-level heading)");
  it.todo("HistoryPage: aria-input-field-name on the Type filter Select");
  it.todo("DashboardPage: aria-progressbar-name on the loading progressbar");
});
