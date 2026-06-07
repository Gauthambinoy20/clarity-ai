import { useState, useCallback } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  Chip,
  CircularProgress,
  Alert,
  Divider,
  useTheme,
} from "@mui/material";
import Grid from "@mui/material/Grid2";
import CompareArrowsOutlinedIcon from "@mui/icons-material/CompareArrowsOutlined";
import SmartToyOutlinedIcon from "@mui/icons-material/SmartToyOutlined";
import { motion, AnimatePresence } from "framer-motion";
import ComparisonView from "@/components/analytics/ComparisonView";
import ExportMenu from "@/components/common/ExportMenu";
import KeyboardShortcuts from "@/components/common/KeyboardShortcuts";
import { useComparison } from "@/hooks/useAnalytics";
import { analyzeText } from "@/utils/api";
import type { ComparisonResult } from "@/types/analytics";
import type { DetectionResult } from "@/types/analysis";

function countWords(text: string): number {
  return text
    .trim()
    .split(/\s+/)
    .filter((w) => w.length > 0).length;
}

export default function ComparePage() {
  const theme = useTheme();
  const [textA, setTextA] = useState("");
  const [textB, setTextB] = useState("");
  const [comparisonResult, setComparisonResult] = useState<ComparisonResult | null>(null);
  const [detectionA, setDetectionA] = useState<DetectionResult | null>(null);
  const [detectionB, setDetectionB] = useState<DetectionResult | null>(null);
  const [detectLoading, setDetectLoading] = useState(false);

  const comparison = useComparison();
  const isLoading = comparison.isPending;

  const wordsA = countWords(textA);
  const wordsB = countWords(textB);
  const canSubmit = wordsA >= 20 && wordsB >= 20;

  const handleCompare = useCallback(() => {
    if (!canSubmit || isLoading) return;
    setDetectionA(null);
    setDetectionB(null);
    comparison.mutate(
      { textA, textB },
      {
        onSuccess: (data) => setComparisonResult(data),
      }
    );
  }, [textA, textB, canSubmit, isLoading, comparison]);

  const handleDetectBoth = useCallback(async () => {
    if (!canSubmit) return;
    setDetectLoading(true);
    try {
      const [resultA, resultB] = await Promise.all([
        analyzeText(textA, "deep"),
        analyzeText(textB, "deep"),
      ]);
      setDetectionA(resultA);
      setDetectionB(resultB);
    } catch {
      // errors handled by interceptor
    } finally {
      setDetectLoading(false);
    }
  }, [textA, textB, canSubmit]);

  const getScoreColor = (score: number) => {
    if (score >= 0.7) return theme.palette.error.main;
    if (score >= 0.4) return theme.palette.warning.main;
    return theme.palette.success.main;
  };

  const getScoreLabel = (score: number) => {
    if (score >= 0.7) return "Likely AI";
    if (score >= 0.4) return "Mixed";
    return "Likely Human";
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
    >
      <KeyboardShortcuts onAnalyze={handleCompare} />

      <Box sx={{ maxWidth: 1200, mx: "auto" }}>
        {/* Header */}
        <Box sx={{ mb: 4 }}>
          <Typography variant="h4" fontWeight={700} gutterBottom>
            Text Comparison
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Compare two texts side by side. Analyze similarity, structural
            differences, and run AI detection on both.
          </Typography>
        </Box>

        {/* Input areas */}
        <Grid container spacing={3} sx={{ mb: 3 }}>
          <Grid size={{ xs: 12, md: 6 }}>
            <Card sx={{ height: "100%" }}>
              <CardContent>
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    mb: 1.5,
                  }}
                >
                  <Typography variant="subtitle2" fontWeight={600} color="primary.main">
                    Text A
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {wordsA} words
                  </Typography>
                </Box>
                <TextField
                  multiline
                  minRows={8}
                  maxRows={16}
                  fullWidth
                  value={textA}
                  onChange={(e) => setTextA(e.target.value)}
                  placeholder="Paste the first text here..."
                  disabled={isLoading}
                  sx={{
                    "& .MuiOutlinedInput-root": {
                      fontSize: "0.95rem",
                      lineHeight: 1.7,
                    },
                  }}
                />
              </CardContent>
            </Card>
          </Grid>
          <Grid size={{ xs: 12, md: 6 }}>
            <Card sx={{ height: "100%" }}>
              <CardContent>
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    mb: 1.5,
                  }}
                >
                  <Typography variant="subtitle2" fontWeight={600} color="secondary.main">
                    Text B
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {wordsB} words
                  </Typography>
                </Box>
                <TextField
                  multiline
                  minRows={8}
                  maxRows={16}
                  fullWidth
                  value={textB}
                  onChange={(e) => setTextB(e.target.value)}
                  placeholder="Paste the second text here..."
                  disabled={isLoading}
                  sx={{
                    "& .MuiOutlinedInput-root": {
                      fontSize: "0.95rem",
                      lineHeight: 1.7,
                    },
                  }}
                />
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        {/* Action buttons */}
        <Box
          sx={{
            display: "flex",
            justifyContent: "center",
            gap: 2,
            mb: 3,
            flexWrap: "wrap",
          }}
        >
          <Button
            variant="contained"
            disabled={!canSubmit || isLoading}
            onClick={handleCompare}
            startIcon={
              isLoading ? (
                <CircularProgress size={18} color="inherit" />
              ) : (
                <CompareArrowsOutlinedIcon />
              )
            }
            sx={{
              background: "linear-gradient(135deg, #7c3aed 0%, #06b6d4 100%)",
              color: "#fff",
              px: 4,
              "&:hover": {
                background: "linear-gradient(135deg, #6d28d9 0%, #0891b2 100%)",
              },
              "&.Mui-disabled": {
                background: "action.disabledBackground",
              },
            }}
          >
            {isLoading ? "Comparing..." : "Compare Texts"}
          </Button>

          <Button
            variant="outlined"
            disabled={!canSubmit || detectLoading}
            onClick={handleDetectBoth}
            startIcon={
              detectLoading ? (
                <CircularProgress size={18} color="inherit" />
              ) : (
                <SmartToyOutlinedIcon />
              )
            }
          >
            {detectLoading ? "Detecting..." : "AI Detect Both"}
          </Button>

          {comparisonResult && (
            <ExportMenu
              data={comparisonResult as unknown as Record<string, unknown>}
              text={`${textA}\n---\n${textB}`}
            />
          )}
        </Box>

        {/* Min words warning */}
        {(wordsA > 0 || wordsB > 0) && !canSubmit && (
          <Alert severity="info" sx={{ mb: 3, borderRadius: 2 }}>
            Both texts need at least 20 words to compare.
            {wordsA < 20 && ` Text A needs ${20 - wordsA} more words.`}
            {wordsB < 20 && ` Text B needs ${20 - wordsB} more words.`}
          </Alert>
        )}

        {/* Error */}
        {comparison.isError && (
          <Alert severity="error" sx={{ mb: 3, borderRadius: 2 }}>
            {comparison.error?.message || "Comparison failed. Please try again."}
          </Alert>
        )}

        {/* AI Detection results */}
        <AnimatePresence>
          {(detectionA || detectionB) && (
            <motion.div
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.3 }}
            >
              <Card sx={{ mb: 3 }}>
                <CardContent>
                  <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                    AI Detection Results
                  </Typography>
                  <Grid container spacing={3} sx={{ mt: 0.5 }}>
                    <Grid size={{ xs: 12, md: 6 }}>
                      <Box
                        sx={{
                          p: 2,
                          borderRadius: 2,
                          border: "1px solid",
                          borderColor: "divider",
                          textAlign: "center",
                        }}
                      >
                        <Typography
                          variant="caption"
                          fontWeight={600}
                          color="primary.main"
                        >
                          Text A
                        </Typography>
                        {detectionA ? (
                          <>
                            <Typography
                              variant="h3"
                              fontWeight={800}
                              sx={{
                                mt: 1,
                                color: getScoreColor(detectionA.overallScore),
                              }}
                            >
                              {(detectionA.overallScore * 100).toFixed(0)}%
                            </Typography>
                            <Chip
                              label={getScoreLabel(detectionA.overallScore)}
                              size="small"
                              sx={{
                                mt: 0.5,
                                fontWeight: 600,
                                backgroundColor: getScoreColor(
                                  detectionA.overallScore
                                ),
                                color: "#fff",
                              }}
                            />
                          </>
                        ) : (
                          <Typography
                            variant="body2"
                            color="text.secondary"
                            sx={{ mt: 2 }}
                          >
                            Not analyzed yet
                          </Typography>
                        )}
                      </Box>
                    </Grid>
                    <Grid size={{ xs: 12, md: 6 }}>
                      <Box
                        sx={{
                          p: 2,
                          borderRadius: 2,
                          border: "1px solid",
                          borderColor: "divider",
                          textAlign: "center",
                        }}
                      >
                        <Typography
                          variant="caption"
                          fontWeight={600}
                          color="secondary.main"
                        >
                          Text B
                        </Typography>
                        {detectionB ? (
                          <>
                            <Typography
                              variant="h3"
                              fontWeight={800}
                              sx={{
                                mt: 1,
                                color: getScoreColor(detectionB.overallScore),
                              }}
                            >
                              {(detectionB.overallScore * 100).toFixed(0)}%
                            </Typography>
                            <Chip
                              label={getScoreLabel(detectionB.overallScore)}
                              size="small"
                              sx={{
                                mt: 0.5,
                                fontWeight: 600,
                                backgroundColor: getScoreColor(
                                  detectionB.overallScore
                                ),
                                color: "#fff",
                              }}
                            />
                          </>
                        ) : (
                          <Typography
                            variant="body2"
                            color="text.secondary"
                            sx={{ mt: 2 }}
                          >
                            Not analyzed yet
                          </Typography>
                        )}
                      </Box>
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Comparison Results */}
        <AnimatePresence>
          {comparisonResult && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.4 }}
            >
              <ComparisonView
                data={comparisonResult}
                textA={textA}
                textB={textB}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </Box>
    </motion.div>
  );
}
