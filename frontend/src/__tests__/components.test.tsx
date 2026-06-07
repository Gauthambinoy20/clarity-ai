/**
 * Render tests for a handful of presentational components.
 *
 * Props are shaped from the real response types in src/types so the tests
 * exercise the components the way the pages actually feed them. The api module
 * is mocked for ExportMenu since its menu actions hit the export endpoints.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { SignalScore, SentenceScore } from "@/types/analysis";
import { renderWithTheme } from "./helpers/providers";

vi.mock("@/utils/api");
import * as api from "@/utils/api";

import SignalBreakdown from "@/components/analysis/SignalBreakdown";
import SentenceHeatmap from "@/components/analysis/SentenceHeatmap";
import PatternHighlighter from "@/components/analysis/PatternHighlighter";
import FileUpload from "@/components/input/FileUpload";
import ExportMenu from "@/components/common/ExportMenu";

const mockedApi = vi.mocked(api);

beforeEach(() => {
  vi.clearAllMocks();
});

// ---------------------------------------------------------------------------
// SignalBreakdown
// ---------------------------------------------------------------------------

describe("SignalBreakdown", () => {
  const signals: SignalScore[] = [
    {
      name: "perplexity",
      score: 0.82,
      weight: 1.5,
      description: "Measures how predictable the token sequence is.",
      category: "statistical",
    },
    {
      name: "burstiness",
      score: 0.41,
      weight: 1,
      description: "Variation in sentence length and complexity.",
      category: "linguistic",
    },
  ];

  it("renders the heading and each signal name", () => {
    renderWithTheme(<SignalBreakdown signals={signals} />);
    expect(screen.getByText("Signal Breakdown")).toBeInTheDocument();
    // Underscores are rendered as spaces; these names have none.
    expect(screen.getByText("perplexity")).toBeInTheDocument();
    expect(screen.getByText("burstiness")).toBeInTheDocument();
  });

  it("shows the rounded percentage for a signal", () => {
    renderWithTheme(<SignalBreakdown signals={signals} />);
    expect(screen.getByText("82%")).toBeInTheDocument();
  });

  it("reveals the description after clicking a signal card", () => {
    renderWithTheme(<SignalBreakdown signals={signals} />);
    fireEvent.click(screen.getByText("perplexity"));
    expect(screen.getByText("Measures how predictable the token sequence is.")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// SentenceHeatmap
// ---------------------------------------------------------------------------

describe("SentenceHeatmap", () => {
  const sentences: SentenceScore[] = [
    {
      text: "This first sentence reads naturally.",
      score: 0.2,
      startIndex: 0,
      endIndex: 36,
      signals: { perplexity: 0.18, burstiness: 0.22 },
    },
    {
      text: "This second sentence looks machine generated.",
      score: 0.91,
      startIndex: 37,
      endIndex: 82,
      signals: { perplexity: 0.93 },
    },
  ];

  it("renders every sentence", () => {
    renderWithTheme(<SentenceHeatmap sentences={sentences} />);
    expect(screen.getByText("This first sentence reads naturally.")).toBeInTheDocument();
    expect(screen.getByText("This second sentence looks machine generated.")).toBeInTheDocument();
  });

  it("opens a popover with per-signal scores when a sentence is clicked", () => {
    renderWithTheme(<SentenceHeatmap sentences={sentences} />);
    fireEvent.click(screen.getByText("This second sentence looks machine generated."));
    expect(screen.getByText("AI Probability:")).toBeInTheDocument();
    expect(screen.getByText("91%")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// PatternHighlighter
// ---------------------------------------------------------------------------

describe("PatternHighlighter", () => {
  const text = "Furthermore, it is important to note that this leverages a robust solution.";
  const data = {
    patterns_found: 3,
    pattern_density: 0.04,
    ai_probability: 0.66,
    pattern_categories: {
      transition: { count: 1, examples: ["Furthermore"] },
    },
    phrase_matches: {
      buzzword: ["leverages", "robust"],
    },
  };

  it("renders the header and the patterns-found chip", () => {
    renderWithTheme(<PatternHighlighter text={text} data={data} />);
    expect(screen.getByText("AI Pattern Highlighter")).toBeInTheDocument();
    expect(screen.getByText("3 patterns found")).toBeInTheDocument();
  });

  it("shows the summary stats derived from the data", () => {
    renderWithTheme(<PatternHighlighter text={text} data={data} />);
    expect(screen.getByText("AI Probability: 66%")).toBeInTheDocument();
    expect(screen.getByText("Categories: 1")).toBeInTheDocument();
  });

  it("renders the analyzed text content", () => {
    renderWithTheme(<PatternHighlighter text={text} data={data} />);
    // The matched word is highlighted in its own span.
    expect(screen.getByText("Furthermore")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// FileUpload
// ---------------------------------------------------------------------------

describe("FileUpload", () => {
  it("renders the drag-and-drop prompt", () => {
    renderWithTheme(<FileUpload onFileContent={vi.fn()} />);
    expect(screen.getByText("Drag & drop a file")).toBeInTheDocument();
    expect(screen.getByText("Supports PDF, DOCX, TXT")).toBeInTheDocument();
  });

  it("calls onFileContent with the file text after a drop", async () => {
    const onFileContent = vi.fn();
    const { container } = renderWithTheme(<FileUpload onFileContent={onFileContent} />);

    const file = new File(["hello from a dropped file"], "essay.txt", {
      type: "text/plain",
    });
    const input = container.querySelector('input[type="file"]') as HTMLInputElement;

    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() =>
      expect(onFileContent).toHaveBeenCalledWith("hello from a dropped file", "essay.txt")
    );
  });
});

// ---------------------------------------------------------------------------
// ExportMenu
// ---------------------------------------------------------------------------

describe("ExportMenu", () => {
  const data = { overallScore: 70, label: "ai" };

  it("renders the export trigger button", () => {
    renderWithTheme(<ExportMenu data={data} text="some text" />);
    expect(screen.getByRole("button", { name: /export/i })).toBeInTheDocument();
  });

  it("opens the menu with each export option", async () => {
    const user = userEvent.setup();
    renderWithTheme(<ExportMenu data={data} text="some text" />);

    await user.click(screen.getByRole("button", { name: /export/i }));

    expect(screen.getByText("Export as PDF")).toBeInTheDocument();
    expect(screen.getByText("Export as JSON")).toBeInTheDocument();
    expect(screen.getByText("Export as CSV")).toBeInTheDocument();
  });

  it("calls the JSON export endpoint when that option is chosen", async () => {
    const user = userEvent.setup();
    mockedApi.exportJson.mockResolvedValue(new Blob(["{}"], { type: "application/json" }));
    // jsdom has no object-URL machinery, so define the bits the click uses.
    const originalCreate = URL.createObjectURL;
    const originalRevoke = URL.revokeObjectURL;
    URL.createObjectURL = vi.fn(() => "blob:fake");
    URL.revokeObjectURL = vi.fn();

    renderWithTheme(<ExportMenu data={data} text="some text" />);
    await user.click(screen.getByRole("button", { name: /export/i }));
    await user.click(screen.getByText("Export as JSON"));

    await waitFor(() => expect(mockedApi.exportJson).toHaveBeenCalledWith(data));

    URL.createObjectURL = originalCreate;
    URL.revokeObjectURL = originalRevoke;
  });

  it("is disabled when the disabled prop is set", () => {
    renderWithTheme(<ExportMenu data={data} text="some text" disabled />);
    expect(screen.getByRole("button", { name: /export/i })).toBeDisabled();
  });
});
