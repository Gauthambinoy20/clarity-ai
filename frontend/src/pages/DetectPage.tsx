import { useState, useCallback } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Tabs,
  Tab,
  Divider,
  Chip,
  Button,
  LinearProgress,
  Paper,
  Tooltip,
  IconButton,
  alpha,
  useTheme,
} from "@mui/material";
import Grid from "@mui/material/Grid2";
import SmartToyOutlinedIcon from "@mui/icons-material/SmartToyOutlined";
import PersonOutlinedIcon from "@mui/icons-material/PersonOutlined";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import RefreshIcon from "@mui/icons-material/Refresh";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import TimerOutlinedIcon from "@mui/icons-material/TimerOutlined";
import DescriptionOutlinedIcon from "@mui/icons-material/DescriptionOutlined";
import SpeedOutlinedIcon from "@mui/icons-material/SpeedOutlined";
import { motion, AnimatePresence } from "framer-motion";
import TextInput from "@/components/input/TextInput";
import FileUpload from "@/components/input/FileUpload";
import LoadingProgress from "@/components/common/LoadingProgress";
import ScoreGauge from "@/components/common/ScoreGauge";
import SignalRadar from "@/components/analysis/SignalRadar";
import SignalBreakdown from "@/components/analysis/SignalBreakdown";
import SentenceHeatmap from "@/components/analysis/SentenceHeatmap";
import GLTRVisualization from "@/components/analysis/GLTRVisualization";
import QuickActionsToolbar from "@/components/advanced/QuickActionsToolbar";
import ShareAnalysis from "@/components/advanced/ShareAnalysis";
import { useDetection } from "@/hooks/useDetection";
import { useAppStore } from "@/stores/appStore";
import type { DetectionResult } from "@/types/analysis";

/* ─── helpers ─────────────────────────────────────────────────────── */

const classificationColor = (label: string) => {
  switch (label) {
    case "ai":
      return "#ef4444";
    case "human":
      return "#22c55e";
    case "mixed":
    default:
      return "#f59e0b";
  }
};

const classificationLabel = (label: string) => {
  switch (label) {
    case "ai":
      return "AI Generated";
    case "human":
      return "Human Written";
    case "mixed":
      return "Mixed Content";
    default:
      return "Uncertain";
  }
};

const classificationIcon = (label: string) => {
  switch (label) {
    case "ai":
      return <SmartToyOutlinedIcon />;
    case "human":
      return <PersonOutlinedIcon />;
    default:
      return <WarningAmberIcon />;
  }
};

/* ─── stat card ───────────────────────────────────────────────────── */

function StatMiniCard({
  icon,
  label,
  value,
  color,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  color: string;
}) {
  const theme = useTheme();
  return (
    <Paper
      elevation={0}
      sx={{
        p: 1.5,
        borderRadius: 2,
        border: `1px solid ${alpha(color, 0.2)}`,
        background: alpha(color, 0.04),
        display: "flex",
        alignItems: "center",
        gap: 1.5,
      }}
    >
      <Box
        sx={{
          width: 36,
          height: 36,
          borderRadius: 1.5,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: alpha(color, 0.12),
          color,
        }}
      >
        {icon}
      </Box>
      <Box>
        <Typography variant="caption" color="text.secondary" sx={{ lineHeight: 1 }}>
          {label}
        </Typography>
        <Typography variant="body2" fontWeight={700}>
          {value}
        </Typography>
      </Box>
    </Paper>
  );
}

/* ─── signal bar (compact) ────────────────────────────────────────── */

function SignalBar({
  name,
  score,
  delay,
}: {
  name: string;
  score: number;
  delay: number;
}) {
  const pct = Math.round(score * 100);
  const barColor =
    pct > 70 ? "#ef4444" : pct > 40 ? "#f59e0b" : "#22c55e";

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay, duration: 0.3 }}
    >
      <Box sx={{ mb: 1 }}>
        <Box sx={{ display: "flex", justifyContent: "space-between", mb: 0.3 }}>
          <Typography variant="caption" fontWeight={500} sx={{ textTransform: "capitalize" }}>
            {name.replace(/_/g, " ")}
          </Typography>
          <Typography variant="caption" fontWeight={700} sx={{ color: barColor }}>
            {pct}%
          </Typography>
        </Box>
        <LinearProgress
          variant="determinate"
          value={pct}
          sx={{
            height: 6,
            borderRadius: 3,
            backgroundColor: alpha(barColor, 0.12),
            "& .MuiLinearProgress-bar": {
              borderRadius: 3,
              backgroundColor: barColor,
            },
          }}
        />
      </Box>
    </motion.div>
  );
}

/* ─── right dashboard panel ───────────────────────────────────────── */

function RightDashboard({ result }: { result: DetectionResult }) {
  const theme = useTheme();
  const [vizTab, setVizTab] = useState(0);
  const color = classificationColor(result.label);

  const signals = result.signals || [];
  const sortedSignals = [...signals].sort(
    (a, b) => (b.ai_probability ?? b.score ?? 0) - (a.ai_probability ?? a.score ?? 0)
  );

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      style={{ height: "100%" }}
    >
      <Box sx={{ display: "flex", flexDirection: "column", gap: 2, height: "100%" }}>
        {/* ── Hero: Score + Classification ── */}
        <Card
          sx={{
            background: `linear-gradient(135deg, ${alpha(color, 0.08)} 0%, ${alpha(
              theme.palette.background.paper,
              1
            )} 100%)`,
            border: `1px solid ${alpha(color, 0.25)}`,
          }}
        >
          <CardContent sx={{ p: 2.5, "&:last-child": { pb: 2.5 } }}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 3 }}>
              {/* Score gauge */}
              <Box sx={{ flexShrink: 0 }}>
                <ScoreGauge
                  score={result.overallScore}
                  confidence={result.confidence}
                  label={classificationLabel(result.label)}
                  size={140}
                />
              </Box>

              {/* Info */}
              <Box sx={{ flex: 1, minWidth: 0 }}>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1.5 }}>
                  <Chip
                    icon={classificationIcon(result.label)}
                    label={classificationLabel(result.label)}
                    sx={{
                      backgroundColor: alpha(color, 0.15),
                      color,
                      fontWeight: 700,
                      fontSize: "0.8rem",
                      "& .MuiChip-icon": { color },
                    }}
                  />
                  <Chip
                    label={`${Math.round(result.confidence * 100)}% confident`}
                    size="small"
                    variant="outlined"
                  />
                </Box>

                {result.attribution && (
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                    Likely model: <strong>{result.attribution}</strong>
                  </Typography>
                )}

                {/* Mini stats row */}
                <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
                  <StatMiniCard
                    icon={<DescriptionOutlinedIcon fontSize="small" />}
                    label="Words"
                    value={String(result.wordCount || "—")}
                    color={theme.palette.info.main}
                  />
                  <StatMiniCard
                    icon={<TimerOutlinedIcon fontSize="small" />}
                    label="Time"
                    value={`${((result.processingTimeMs || 0) / 1000).toFixed(1)}s`}
                    color={theme.palette.secondary.main}
                  />
                  <StatMiniCard
                    icon={<SpeedOutlinedIcon fontSize="small" />}
                    label="Signals"
                    value={`${signals.length}`}
                    color={theme.palette.primary.main}
                  />
                </Box>
              </Box>
            </Box>
          </CardContent>
        </Card>

        {/* ── Signal Scores ── */}
        <Card sx={{ flex: 1, overflow: "auto" }}>
          <CardContent sx={{ p: 2, "&:last-child": { pb: 2 } }}>
            <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 1.5 }}>
              Detection Signals
            </Typography>

            {sortedSignals.length > 0 ? (
              sortedSignals.map((sig, i) => (
                <SignalBar
                  key={sig.signal || i}
                  name={sig.signal || `Signal ${i + 1}`}
                  score={sig.ai_probability ?? sig.score ?? 0}
                  delay={i * 0.05}
                />
              ))
            ) : (
              <Typography variant="body2" color="text.secondary">
                Run deep mode for full signal breakdown.
              </Typography>
            )}
          </CardContent>
        </Card>

        {/* ── Radar Chart ── */}
        {signals.length > 2 && (
          <Card>
            <CardContent sx={{ p: 2, "&:last-child": { pb: 2 } }}>
              <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 1 }}>
                Signal Radar
              </Typography>
              <Box sx={{ height: 250 }}>
                <SignalRadar signals={signals} />
              </Box>
            </CardContent>
          </Card>
        )}

        {/* ── Sentence Heatmap / GLTR Tabs ── */}
        <Card>
          <CardContent sx={{ p: 2, "&:last-child": { pb: 2 } }}>
            <Tabs value={vizTab} onChange={(_, v) => setVizTab(v)} sx={{ mb: 1.5 }}>
              <Tab label="Sentence Heatmap" sx={{ fontSize: "0.75rem", minHeight: 36 }} />
              <Tab label="GLTR Tokens" sx={{ fontSize: "0.75rem", minHeight: 36 }} />
            </Tabs>
            <Divider sx={{ mb: 1.5 }} />

            {vizTab === 0 && result.sentences && result.sentences.length > 0 && (
              <Box sx={{ maxHeight: 300, overflow: "auto" }}>
                <SentenceHeatmap sentences={result.sentences} />
              </Box>
            )}
            {vizTab === 0 && (!result.sentences || result.sentences.length === 0) && (
              <Typography variant="body2" color="text.secondary">
                Run deep mode for sentence-level analysis.
              </Typography>
            )}
            {vizTab === 1 && result.gltrTokens && result.gltrTokens.length > 0 && (
              <Box sx={{ maxHeight: 300, overflow: "auto" }}>
                <GLTRVisualization tokens={result.gltrTokens} />
              </Box>
            )}
            {vizTab === 1 && (!result.gltrTokens || result.gltrTokens.length === 0) && (
              <Typography variant="body2" color="text.secondary">
                GLTR data not available in fast mode.
              </Typography>
            )}
          </CardContent>
        </Card>
      </Box>
    </motion.div>
  );
}

/* ─── empty state for right panel ─────────────────────────────────── */

function EmptyDashboard() {
  const theme = useTheme();
  return (
    <Box
      sx={{
        height: "100%",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        textAlign: "center",
        p: 4,
      }}
    >
      <Box
        sx={{
          width: 80,
          height: 80,
          borderRadius: "50%",
          background: `linear-gradient(135deg, ${alpha(
            theme.palette.primary.main,
            0.1
          )}, ${alpha(theme.palette.secondary.main, 0.1)})`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          mb: 3,
        }}
      >
        <SmartToyOutlinedIcon
          sx={{ fontSize: 36, color: theme.palette.primary.main, opacity: 0.6 }}
        />
      </Box>
      <Typography variant="h6" fontWeight={600} gutterBottom>
        Analysis Dashboard
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 300 }}>
        Paste or upload text on the left and click <strong>Analyze</strong> to see
        detailed AI detection results with signal breakdown, heatmaps, and more.
      </Typography>

      <Box sx={{ mt: 4, display: "flex", gap: 2, flexWrap: "wrap", justifyContent: "center" }}>
        {[
          { label: "16 Detection Signals", icon: <CheckCircleOutlineIcon fontSize="small" /> },
          { label: "Sentence Heatmap", icon: <CheckCircleOutlineIcon fontSize="small" /> },
          { label: "GLTR Token Analysis", icon: <CheckCircleOutlineIcon fontSize="small" /> },
          { label: "Model Attribution", icon: <CheckCircleOutlineIcon fontSize="small" /> },
        ].map((f) => (
          <Chip
            key={f.label}
            icon={f.icon}
            label={f.label}
            size="small"
            variant="outlined"
            sx={{ opacity: 0.6 }}
          />
        ))}
      </Box>
    </Box>
  );
}

/* ─── MAIN PAGE ───────────────────────────────────────────────────── */

export default function DetectPage() {
  const [inputTab, setInputTab] = useState(0);
  const detection = useDetection();
  const { detectionResult, isAnalyzing } = useAppStore();
  const theme = useTheme();

  const handleSubmit = useCallback(
    (text: string, mode: string) => {
      detection.mutate({ text, mode });
    },
    [detection]
  );

  const handleFileContent = useCallback(
    (text: string, _filename: string) => {
      detection.mutate({ text, mode: "deep" });
    },
    [detection]
  );

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
      style={{ height: "100%" }}
    >
      {/* Header */}
      <Box sx={{ mb: 3, display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
        <Box>
          <Typography variant="h4" fontWeight={800} gutterBottom>
            AI Content Detection
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Paste text on the left — see real-time analysis results on the right.
          </Typography>
        </Box>
        {detectionResult && (
          <ShareAnalysis
            analysisId={detectionResult.id}
            analysisData={detectionResult as unknown as Record<string, unknown>}
            variant="button"
          />
        )}
      </Box>

      {/* Split layout: Left = Input, Right = Dashboard */}
      <Grid container spacing={3} sx={{ height: "calc(100vh - 200px)", minHeight: 600 }}>
        {/* ══════════ LEFT PANEL: Input ══════════ */}
        <Grid size={{ xs: 12, lg: 5 }}>
          <Box sx={{ display: "flex", flexDirection: "column", gap: 2, height: "100%" }}>
            {/* Input Card */}
            <Card sx={{ flex: 1, display: "flex", flexDirection: "column" }}>
              <CardContent sx={{ flex: 1, display: "flex", flexDirection: "column", p: 2.5, "&:last-child": { pb: 2.5 } }}>
                <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 1.5 }}>
                  <Tabs
                    value={inputTab}
                    onChange={(_, v) => setInputTab(v)}
                    sx={{
                      minHeight: 36,
                      "& .MuiTab-root": { minHeight: 36, fontSize: "0.8rem", py: 0 },
                    }}
                  >
                    <Tab label="Paste Text" />
                    <Tab label="Upload File" />
                  </Tabs>
                  <Tooltip title="Minimum 50 words for accurate analysis">
                    <IconButton size="small">
                      <HelpOutlineIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                </Box>

                <Divider sx={{ mb: 2 }} />

                <Box sx={{ flex: 1 }}>
                  {inputTab === 0 && (
                    <TextInput
                      onSubmit={handleSubmit}
                      isLoading={isAnalyzing}
                      placeholder="Paste the text you want to analyze for AI generation..."
                    />
                  )}
                  {inputTab === 1 && (
                    <FileUpload
                      onFileContent={handleFileContent}
                      disabled={isAnalyzing}
                    />
                  )}
                </Box>
              </CardContent>
            </Card>

            {/* Loading indicator */}
            <AnimatePresence>
              {isAnalyzing && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                >
                  <Card>
                    <CardContent sx={{ p: 2, "&:last-child": { pb: 2 } }}>
                      <LoadingProgress isLoading={isAnalyzing} />
                    </CardContent>
                  </Card>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Error */}
            {detection.isError && (
              <Card sx={{ borderColor: "error.main", border: 1 }}>
                <CardContent sx={{ p: 2, "&:last-child": { pb: 2 } }}>
                  <Typography color="error" variant="body2">
                    {detection.error?.message || "Analysis failed. Please try again."}
                  </Typography>
                  <Button
                    size="small"
                    startIcon={<RefreshIcon />}
                    onClick={() => detection.reset()}
                    sx={{ mt: 1 }}
                  >
                    Retry
                  </Button>
                </CardContent>
              </Card>
            )}

            {/* Quick tips when no result */}
            {!detectionResult && !isAnalyzing && (
              <Card
                sx={{
                  background: alpha(theme.palette.info.main, 0.04),
                  border: `1px solid ${alpha(theme.palette.info.main, 0.15)}`,
                }}
              >
                <CardContent sx={{ p: 2, "&:last-child": { pb: 2 } }}>
                  <Typography variant="subtitle2" fontWeight={600} sx={{ mb: 1 }}>
                    Tips for best results
                  </Typography>
                  <Box component="ul" sx={{ m: 0, pl: 2, "& li": { mb: 0.5 } }}>
                    <Typography component="li" variant="caption" color="text.secondary">
                      Paste at least 50 words for reliable detection
                    </Typography>
                    <Typography component="li" variant="caption" color="text.secondary">
                      Use "Deep" mode for all 16 signals and sentence-level analysis
                    </Typography>
                    <Typography component="li" variant="caption" color="text.secondary">
                      "Fast" mode uses 3 signals and returns in under 2 seconds
                    </Typography>
                    <Typography component="li" variant="caption" color="text.secondary">
                      Longer texts (&gt;200 words) produce more accurate results
                    </Typography>
                  </Box>
                </CardContent>
              </Card>
            )}
          </Box>
        </Grid>

        {/* ══════════ RIGHT PANEL: Dashboard ══════════ */}
        <Grid size={{ xs: 12, lg: 7 }}>
          <Box
            sx={{
              height: "100%",
              overflow: "auto",
              borderRadius: 3,
              border: `1px solid ${alpha(theme.palette.divider, 0.5)}`,
              background: alpha(theme.palette.background.paper, 0.3),
              p: detectionResult ? 0 : 2,
            }}
          >
            <AnimatePresence mode="wait">
              {detectionResult && !isAnalyzing ? (
                <Box sx={{ p: 2, display: "flex", flexDirection: "column", gap: 2 }} key="results">
                  <RightDashboard result={detectionResult} />
                  <QuickActionsToolbar text={detectionResult.text} />
                </Box>
              ) : isAnalyzing ? (
                <Box
                  key="loading"
                  sx={{
                    height: "100%",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                  >
                    <Box sx={{ textAlign: "center" }}>
                      <Box
                        sx={{
                          width: 60,
                          height: 60,
                          borderRadius: "50%",
                          border: `3px solid ${alpha(theme.palette.primary.main, 0.3)}`,
                          borderTopColor: theme.palette.primary.main,
                          animation: "spin 1s linear infinite",
                          mx: "auto",
                          mb: 2,
                          "@keyframes spin": {
                            "0%": { transform: "rotate(0deg)" },
                            "100%": { transform: "rotate(360deg)" },
                          },
                        }}
                      />
                      <Typography variant="body2" color="text.secondary">
                        Analyzing text across 16 signals...
                      </Typography>
                    </Box>
                  </motion.div>
                </Box>
              ) : (
                <Box key="empty" sx={{ height: "100%" }}>
                  <EmptyDashboard />
                </Box>
              )}
            </AnimatePresence>
          </Box>
        </Grid>
      </Grid>
    </motion.div>
  );
}
