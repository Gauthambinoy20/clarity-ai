import { useState, useMemo } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  Paper,
  Tooltip,
  Divider,
} from "@mui/material";
import { motion, AnimatePresence } from "framer-motion";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface PatternMatch {
  matched: string;
  pattern?: string;
  model?: string;
}

interface PatternCategory {
  count: number;
  examples: string[];
}

interface PatternData {
  patterns_found: number;
  pattern_density: number;
  pattern_categories: Record<string, PatternCategory>;
  phrase_matches?: Record<string, string[]>;
  ai_probability: number;
}

interface PatternHighlighterProps {
  text: string;
  data: PatternData;
}

// ---------------------------------------------------------------------------
// Category styling
// ---------------------------------------------------------------------------

const CATEGORY_STYLES: Record<string, { color: string; label: string; bgColor: string }> = {
  transition: { color: "#3b82f6", label: "Transition", bgColor: "#3b82f620" },
  opening: { color: "#a855f7", label: "Opening", bgColor: "#a855f720" },
  closing: { color: "#ef4444", label: "Closing", bgColor: "#ef444420" },
  hedging: { color: "#eab308", label: "Hedging", bgColor: "#eab30820" },
  ai_opener: { color: "#f97316", label: "AI Opener", bgColor: "#f9731620" },
  numbered_list: { color: "#f97316", label: "Numbered List", bgColor: "#f9731620" },
  bullet_bold: { color: "#f97316", label: "Bullet Bold", bgColor: "#f9731620" },
  bullet_pattern: { color: "#f97316", label: "Bullet Pattern", bgColor: "#f9731620" },
  markdown_bold: { color: "#f97316", label: "Markdown Bold", bgColor: "#f9731620" },
  markdown_header: { color: "#f97316", label: "Markdown Header", bgColor: "#f9731620" },
  emoji_bullet: { color: "#f97316", label: "Emoji Bullet", bgColor: "#f9731620" },
  code_block: { color: "#f97316", label: "Code Block", bgColor: "#f9731620" },
};

// Group mappings for the legend
const LEGEND_GROUPS: { key: string; label: string; color: string; description: string }[] = [
  { key: "buzzword", label: "AI Buzzwords", color: "#f97316", description: "Phrases frequently overused by AI models" },
  { key: "transition", label: "Transitions", color: "#3b82f6", description: "Formulaic transition phrases AI overuses" },
  { key: "opening", label: "Openings", color: "#a855f7", description: "Common AI opening sentence patterns" },
  { key: "closing", label: "Closings", color: "#ef4444", description: "Typical AI closing/summary patterns" },
  { key: "hedging", label: "Hedging", color: "#eab308", description: "Hedging language and qualifiers" },
];

// ---------------------------------------------------------------------------
// Build highlighted spans
// ---------------------------------------------------------------------------

interface HighlightSpan {
  start: number;
  end: number;
  text: string;
  category: string;
}

function buildHighlightSpans(
  text: string,
  patternCategories: Record<string, PatternCategory>,
  phraseMatches?: Record<string, string[]>,
): HighlightSpan[] {
  const spans: HighlightSpan[] = [];
  const lowerText = text.toLowerCase();

  // Highlight regex pattern matches
  for (const [category, data] of Object.entries(patternCategories)) {
    for (const example of data.examples) {
      const lowerExample = example.toLowerCase().trim();
      if (!lowerExample) continue;

      let searchFrom = 0;
      while (searchFrom < lowerText.length) {
        const idx = lowerText.indexOf(lowerExample, searchFrom);
        if (idx === -1) break;
        spans.push({
          start: idx,
          end: idx + lowerExample.length,
          text: text.substring(idx, idx + lowerExample.length),
          category,
        });
        searchFrom = idx + 1;
      }
    }
  }

  // Highlight phrase matches (buzzwords)
  if (phraseMatches) {
    for (const [, phrases] of Object.entries(phraseMatches)) {
      for (const phrase of phrases) {
        const lowerPhrase = phrase.toLowerCase();
        let searchFrom = 0;
        while (searchFrom < lowerText.length) {
          const idx = lowerText.indexOf(lowerPhrase, searchFrom);
          if (idx === -1) break;
          spans.push({
            start: idx,
            end: idx + lowerPhrase.length,
            text: text.substring(idx, idx + lowerPhrase.length),
            category: "buzzword",
          });
          searchFrom = idx + 1;
        }
      }
    }
  }

  // Sort by start position and remove overlaps
  spans.sort((a, b) => a.start - b.start);
  const merged: HighlightSpan[] = [];
  for (const span of spans) {
    if (merged.length === 0 || span.start >= merged[merged.length - 1].end) {
      merged.push(span);
    }
  }

  return merged;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function PatternHighlighter({ text, data }: PatternHighlighterProps) {
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  const spans = useMemo(
    () => buildHighlightSpans(text, data.pattern_categories, data.phrase_matches),
    [text, data.pattern_categories, data.phrase_matches],
  );

  // Count per category
  const categoryCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const span of spans) {
      const cat = span.category;
      counts[cat] = (counts[cat] || 0) + 1;
    }
    return counts;
  }, [spans]);

  // Render highlighted text
  const renderedText = useMemo(() => {
    if (spans.length === 0) {
      return [<span key="plain">{text}</span>];
    }

    const elements: JSX.Element[] = [];
    let lastEnd = 0;

    for (let i = 0; i < spans.length; i++) {
      const span = spans[i];

      // Text before this span
      if (span.start > lastEnd) {
        elements.push(
          <span key={`text-${i}`}>
            {text.substring(lastEnd, span.start)}
          </span>,
        );
      }

      // The category style
      const style = CATEGORY_STYLES[span.category] || {
        color: "#f97316",
        bgColor: "#f9731620",
        label: span.category,
      };

      const isFiltered = selectedCategory !== null && span.category !== selectedCategory;

      elements.push(
        <Tooltip
          key={`hl-${i}`}
          title={
            <Box>
              <Typography variant="caption" fontWeight={600}>
                {style.label || span.category}
              </Typography>
              <Typography variant="caption" display="block">
                Matched: "{span.text}"
              </Typography>
            </Box>
          }
          arrow
          placement="top"
        >
          <span
            style={{
              backgroundColor: isFiltered ? "transparent" : style.bgColor,
              color: isFiltered ? "inherit" : style.color,
              borderBottom: isFiltered ? "none" : `2px solid ${style.color}`,
              padding: "1px 2px",
              borderRadius: 3,
              cursor: "pointer",
              transition: "all 0.2s ease",
              opacity: isFiltered ? 0.5 : 1,
            }}
          >
            {text.substring(span.start, span.end)}
          </span>
        </Tooltip>,
      );

      lastEnd = span.end;
    }

    // Text after last span
    if (lastEnd < text.length) {
      elements.push(
        <span key="text-end">{text.substring(lastEnd)}</span>,
      );
    }

    return elements;
  }, [text, spans, selectedCategory]);

  return (
    <Card>
      <CardContent>
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
          <Typography variant="h6" fontWeight={700}>
            AI Pattern Highlighter
          </Typography>
          <Chip
            label={`${data.patterns_found} patterns found`}
            size="small"
            color={data.patterns_found > 10 ? "error" : data.patterns_found > 5 ? "warning" : "success"}
          />
        </Box>

        {/* Legend */}
        <Paper
          variant="outlined"
          sx={{ p: 1.5, mb: 2, display: "flex", flexWrap: "wrap", gap: 1 }}
        >
          {LEGEND_GROUPS.map((group) => {
            const count = categoryCounts[group.key] || 0;
            const isActive = selectedCategory === group.key;

            return (
              <Tooltip key={group.key} title={group.description} arrow>
                <Chip
                  label={
                    <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                      <Box
                        sx={{
                          width: 8,
                          height: 8,
                          borderRadius: "50%",
                          backgroundColor: group.color,
                        }}
                      />
                      {group.label}
                      {count > 0 && (
                        <Chip
                          label={count}
                          size="small"
                          sx={{
                            height: 16,
                            fontSize: "0.6rem",
                            ml: 0.5,
                            backgroundColor: `${group.color}30`,
                            color: group.color,
                          }}
                        />
                      )}
                    </Box>
                  }
                  size="small"
                  variant={isActive ? "filled" : "outlined"}
                  onClick={() =>
                    setSelectedCategory(isActive ? null : group.key)
                  }
                  sx={{
                    cursor: "pointer",
                    borderColor: isActive ? group.color : undefined,
                    backgroundColor: isActive ? `${group.color}20` : undefined,
                  }}
                />
              </Tooltip>
            );
          })}
          {selectedCategory && (
            <Chip
              label="Clear filter"
              size="small"
              variant="outlined"
              onDelete={() => setSelectedCategory(null)}
              sx={{ ml: 1 }}
            />
          )}
        </Paper>

        <Divider sx={{ mb: 2 }} />

        {/* Highlighted Text */}
        <AnimatePresence>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.4 }}
          >
            <Paper
              variant="outlined"
              sx={{
                p: 2.5,
                lineHeight: 1.8,
                fontSize: "0.95rem",
                whiteSpace: "pre-wrap",
                maxHeight: 500,
                overflow: "auto",
              }}
            >
              {renderedText}
            </Paper>
          </motion.div>
        </AnimatePresence>

        {/* Summary Stats */}
        <Box sx={{ display: "flex", gap: 2, mt: 2, flexWrap: "wrap" }}>
          <Typography variant="caption" color="text.secondary">
            Pattern Density: {(data.pattern_density * 100).toFixed(2)}%
          </Typography>
          <Typography variant="caption" color="text.secondary">
            AI Probability: {Math.round(data.ai_probability * 100)}%
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Categories: {Object.keys(data.pattern_categories).length}
          </Typography>
        </Box>
      </CardContent>
    </Card>
  );
}
