import { useState, useCallback } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Tabs,
  Tab,
  Button,
  Divider,
  TextField,
  Chip,
  CircularProgress,
  Alert,
} from "@mui/material";
import PlayArrowRoundedIcon from "@mui/icons-material/PlayArrowRounded";
import RocketLaunchOutlinedIcon from "@mui/icons-material/RocketLaunchOutlined";
import { motion, AnimatePresence } from "framer-motion";
import ReadabilityPanel from "@/components/analytics/ReadabilityPanel";
import ToneAnalyzer from "@/components/analytics/ToneAnalyzer";
import GrammarChecker from "@/components/analytics/GrammarChecker";
import TextStatisticsPanel from "@/components/analytics/TextStatisticsPanel";
import WritingSuggestions from "@/components/analytics/WritingSuggestions";
import CitationChecker from "@/components/analytics/CitationChecker";
import ParaphraseDetector from "@/components/analytics/ParaphraseDetector";
import FactChecker from "@/components/analytics/FactChecker";
import SEOAnalyzer from "@/components/analytics/SEOAnalyzer";
import ExportMenu from "@/components/common/ExportMenu";
import KeyboardShortcuts from "@/components/common/KeyboardShortcuts";
import { useFullAnalytics } from "@/hooks/useAnalytics";
import { analyzeParaphrase, checkFacts, analyzeSEO } from "@/utils/api";
import type {
  FullAnalyticsResult,
  ParaphraseResult,
  FactCheckResult,
  SEOResult,
} from "@/types/analytics";

function countWords(text: string): number {
  return text
    .trim()
    .split(/\s+/)
    .filter((w) => w.length > 0).length;
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel({ children, value, index }: TabPanelProps) {
  return (
    <Box role="tabpanel" hidden={value !== index} sx={{ pt: 3 }}>
      {value === index && (
        <AnimatePresence mode="wait">
          <motion.div
            key={index}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.25 }}
          >
            {children}
          </motion.div>
        </AnimatePresence>
      )}
    </Box>
  );
}

export default function AnalyticsPage() {
  const [text, setText] = useState("");
  const [tab, setTab] = useState(0);
  const [result, setResult] = useState<FullAnalyticsResult | null>(null);
  const [paraphraseResult, setParaphraseResult] = useState<ParaphraseResult | null>(null);
  const [factResult, setFactResult] = useState<FactCheckResult | null>(null);
  const [seoResult, setSeoResult] = useState<SEOResult | null>(null);

  const fullAnalytics = useFullAnalytics();
  const wordCount = countWords(text);
  const isMinWords = wordCount >= 50;
  const isLoading = fullAnalytics.isPending;

  const handleAnalyze = useCallback(() => {
    if (!isMinWords || isLoading) return;
    fullAnalytics.mutate(text, {
      onSuccess: (data) => setResult(data),
    });
    // Run additional analyses in parallel
    analyzeParaphrase(text)
      .then((data) => setParaphraseResult(data))
      .catch(() => {});
    checkFacts(text)
      .then((data) => setFactResult(data))
      .catch(() => {});
    analyzeSEO(text)
      .then((data) => setSeoResult(data))
      .catch(() => {});
  }, [text, isMinWords, isLoading, fullAnalytics]);

  const tabLabels = [
    "Readability",
    "Tone",
    "Grammar",
    "Statistics",
    "Suggestions",
    "Citations",
    "Paraphrase",
    "Facts",
    "SEO",
  ];

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
    >
      <KeyboardShortcuts onAnalyze={handleAnalyze} />

      <Box sx={{ maxWidth: 1200, mx: "auto" }}>
        {/* Header */}
        <Box sx={{ mb: 4 }}>
          <Typography variant="h4" fontWeight={700} gutterBottom>
            Text Analytics
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Comprehensive writing analysis including readability, tone, grammar,
            statistics, and suggestions.
          </Typography>
        </Box>

        {/* Input */}
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <TextField
              multiline
              minRows={5}
              maxRows={14}
              fullWidth
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Paste or type text to analyze..."
              disabled={isLoading}
              sx={{
                "& .MuiOutlinedInput-root": {
                  fontSize: "1rem",
                  lineHeight: 1.7,
                },
              }}
            />

            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                mt: 1.5,
                flexWrap: "wrap",
                gap: 1,
              }}
            >
              <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
                <Typography variant="caption" color="text.secondary">
                  {wordCount} words
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {text.length} chars
                </Typography>
                {wordCount > 0 && !isMinWords && (
                  <motion.div
                    initial={{ opacity: 0, x: -5 }}
                    animate={{ opacity: 1, x: 0 }}
                  >
                    <Chip
                      label={`${50 - wordCount} more words needed`}
                      size="small"
                      color="warning"
                      variant="outlined"
                    />
                  </motion.div>
                )}
              </Box>

              <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
                {result && (
                  <ExportMenu
                    data={result as unknown as Record<string, unknown>}
                    text={text}
                  />
                )}
                <Button
                  variant="contained"
                  disabled={!isMinWords || isLoading}
                  onClick={handleAnalyze}
                  startIcon={
                    isLoading ? (
                      <CircularProgress size={18} color="inherit" />
                    ) : (
                      <RocketLaunchOutlinedIcon />
                    )
                  }
                  sx={{
                    background:
                      "linear-gradient(135deg, #7c3aed 0%, #06b6d4 100%)",
                    color: "#fff",
                    "&:hover": {
                      background:
                        "linear-gradient(135deg, #6d28d9 0%, #0891b2 100%)",
                    },
                    "&.Mui-disabled": {
                      background: "action.disabledBackground",
                    },
                  }}
                >
                  {isLoading ? "Analyzing..." : "Run All Analyses"}
                </Button>
              </Box>
            </Box>
          </CardContent>
        </Card>

        {/* Error */}
        {fullAnalytics.isError && (
          <Alert severity="error" sx={{ mb: 3, borderRadius: 2 }}>
            {fullAnalytics.error?.message || "Analysis failed. Please try again."}
          </Alert>
        )}

        {/* Results */}
        {result && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
          >
            <Card>
              <CardContent sx={{ pb: 0 }}>
                <Tabs
                  value={tab}
                  onChange={(_, v) => setTab(v)}
                  variant="scrollable"
                  scrollButtons="auto"
                >
                  {tabLabels.map((label) => (
                    <Tab key={label} label={label} />
                  ))}
                </Tabs>
              </CardContent>
              <Divider />
              <CardContent>
                <TabPanel value={tab} index={0}>
                  <ReadabilityPanel data={result.readability} />
                </TabPanel>
                <TabPanel value={tab} index={1}>
                  <ToneAnalyzer data={result.tone} />
                </TabPanel>
                <TabPanel value={tab} index={2}>
                  <GrammarChecker data={result.grammar} />
                </TabPanel>
                <TabPanel value={tab} index={3}>
                  <TextStatisticsPanel data={result.statistics} />
                </TabPanel>
                <TabPanel value={tab} index={4}>
                  <WritingSuggestions data={result.suggestions} />
                </TabPanel>
                <TabPanel value={tab} index={5}>
                  <CitationChecker data={result.citations} />
                </TabPanel>
                <TabPanel value={tab} index={6}>
                  {paraphraseResult ? (
                    <ParaphraseDetector data={paraphraseResult} />
                  ) : (
                    <Box sx={{ textAlign: "center", py: 4 }}>
                      <CircularProgress size={28} />
                      <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                        Analyzing paraphrases...
                      </Typography>
                    </Box>
                  )}
                </TabPanel>
                <TabPanel value={tab} index={7}>
                  {factResult ? (
                    <FactChecker data={factResult} />
                  ) : (
                    <Box sx={{ textAlign: "center", py: 4 }}>
                      <CircularProgress size={28} />
                      <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                        Checking facts...
                      </Typography>
                    </Box>
                  )}
                </TabPanel>
                <TabPanel value={tab} index={8}>
                  {seoResult ? (
                    <SEOAnalyzer data={seoResult} />
                  ) : (
                    <Box sx={{ textAlign: "center", py: 4 }}>
                      <CircularProgress size={28} />
                      <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                        Analyzing SEO...
                      </Typography>
                    </Box>
                  )}
                </TabPanel>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </Box>
    </motion.div>
  );
}
