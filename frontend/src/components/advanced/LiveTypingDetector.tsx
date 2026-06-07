import { useState, useEffect, useRef, useCallback } from "react";
import {
  Box,
  TextField,
  Typography,
  alpha,
  useTheme,
  Chip,
} from "@mui/material";
import AutorenewIcon from "@mui/icons-material/Autorenew";
import { motion, AnimatePresence } from "framer-motion";

/* ─── Types ──────────────────────────────────────────────────────── */

export interface LiveSignal {
  name: string;
  score: number;
}

export interface LiveDetectionResult {
  score: number;
  signals: LiveSignal[];
}

interface LiveTypingDetectorProps {
  onAnalyze?: (text: string) => Promise<LiveDetectionResult>;
  debounceMs?: number;
}

/* ─── Score badge color helper ───────────────────────────────────── */

const getScoreColor = (score: number) => {
  if (score > 70) return "#ef4444";
  if (score > 40) return "#f59e0b";
  return "#22c55e";
};

/* ─── Mini Signal Bar ────────────────────────────────────────────── */

function MiniSignalBar({ name, score, delay }: { name: string; score: number; delay: number }) {
  const theme = useTheme();
  const pct = Math.round(score * 100);
  const color = getScoreColor(pct);

  return (
    <motion.div
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay, duration: 0.25 }}
    >
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 0.5 }}>
        <Typography
          variant="caption"
          sx={{ width: 100, textTransform: "capitalize", fontSize: "0.7rem" }}
          noWrap
        >
          {name.replace(/_/g, " ")}
        </Typography>
        <Box
          sx={{
            flex: 1,
            height: 5,
            borderRadius: 2.5,
            backgroundColor: alpha(color, 0.12),
            overflow: "hidden",
          }}
        >
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${pct}%` }}
            transition={{ duration: 0.5, ease: "easeOut" }}
            style={{
              height: "100%",
              borderRadius: 2.5,
              backgroundColor: color,
            }}
          />
        </Box>
        <Typography variant="caption" fontWeight={700} sx={{ color, width: 30, textAlign: "right" }}>
          {pct}%
        </Typography>
      </Box>
    </motion.div>
  );
}

/* ─── Main Component ─────────────────────────────────────────────── */

export default function LiveTypingDetector({
  onAnalyze,
  debounceMs = 500,
}: LiveTypingDetectorProps) {
  const theme = useTheme();
  const [text, setText] = useState("");
  const [score, setScore] = useState<number | null>(null);
  const [signals, setSignals] = useState<LiveSignal[]>([]);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const debounceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const wordCount = text.trim() ? text.trim().split(/\s+/).length : 0;

  const runAnalysis = useCallback(
    async (input: string) => {
      if (input.trim().split(/\s+/).length < 10) {
        setScore(null);
        setSignals([]);
        return;
      }

      setIsAnalyzing(true);
      try {
        if (onAnalyze) {
          const result = await onAnalyze(input);
          setScore(result.score);
          setSignals(result.signals.slice(0, 3));
        } else {
          // Demo mode
          await new Promise((r) => setTimeout(r, 400));
          const fakeScore = Math.round(20 + Math.random() * 60);
          setScore(fakeScore);
          setSignals([
            { name: "perplexity", score: 0.3 + Math.random() * 0.5 },
            { name: "burstiness", score: 0.2 + Math.random() * 0.6 },
            { name: "vocabulary_richness", score: 0.4 + Math.random() * 0.4 },
          ]);
        }
      } catch {
        // Silently fail for live typing
      } finally {
        setIsAnalyzing(false);
      }
    },
    [onAnalyze]
  );

  useEffect(() => {
    if (debounceTimer.current) clearTimeout(debounceTimer.current);
    if (!text.trim()) {
      setScore(null);
      setSignals([]);
      return;
    }
    debounceTimer.current = setTimeout(() => {
      runAnalysis(text);
    }, debounceMs);
    return () => {
      if (debounceTimer.current) clearTimeout(debounceTimer.current);
    };
  }, [text, debounceMs, runAnalysis]);

  const scoreColor = score !== null ? getScoreColor(score) : theme.palette.text.secondary;

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
      {/* Text area with floating badge */}
      <Box sx={{ position: "relative" }}>
        <TextField
          multiline
          rows={10}
          fullWidth
          placeholder="Start typing or paste text here for real-time AI detection..."
          value={text}
          onChange={(e) => setText(e.target.value)}
          sx={{
            "& .MuiOutlinedInput-root": {
              fontSize: "0.95rem",
              lineHeight: 1.7,
              borderRadius: 3,
            },
          }}
        />

        {/* Floating score badge */}
        <AnimatePresence>
          {score !== null && (
            <motion.div
              initial={{ opacity: 0, scale: 0.5 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.5 }}
              transition={{ type: "spring", stiffness: 300, damping: 20 }}
              style={{
                position: "absolute",
                top: 12,
                right: 12,
                zIndex: 10,
              }}
            >
              <Box
                sx={{
                  width: 56,
                  height: 56,
                  borderRadius: "50%",
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  backgroundColor: alpha(scoreColor, 0.12),
                  border: `2px solid ${alpha(scoreColor, 0.4)}`,
                  backdropFilter: "blur(8px)",
                }}
              >
                <motion.div
                  key={score}
                  initial={{ scale: 1.3 }}
                  animate={{ scale: 1 }}
                  transition={{ type: "spring", stiffness: 400 }}
                >
                  <Typography variant="body1" fontWeight={800} sx={{ color: scoreColor, lineHeight: 1 }}>
                    {score}
                  </Typography>
                </motion.div>
                <Typography variant="caption" sx={{ fontSize: "0.55rem", color: scoreColor }}>
                  AI %
                </Typography>
              </Box>
            </motion.div>
          )}
        </AnimatePresence>
      </Box>

      {/* Word count + Analyzing indicator */}
      <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
        <Typography variant="caption" color="text.secondary">
          {wordCount} {wordCount === 1 ? "word" : "words"}
        </Typography>
        {wordCount > 0 && wordCount < 10 && (
          <Typography variant="caption" color="warning.main" sx={{ fontStyle: "italic" }}>
            Type at least 10 words for analysis
          </Typography>
        )}
        <Box sx={{ flex: 1 }} />
        <AnimatePresence>
          {isAnalyzing && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <Chip
                icon={
                  <AutorenewIcon
                    sx={{
                      fontSize: 16,
                      animation: "spin 1s linear infinite",
                      "@keyframes spin": {
                        "0%": { transform: "rotate(0deg)" },
                        "100%": { transform: "rotate(360deg)" },
                      },
                    }}
                  />
                }
                label="Analyzing..."
                size="small"
                variant="outlined"
                sx={{ fontSize: "0.7rem" }}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </Box>

      {/* Mini signal bars */}
      <AnimatePresence>
        {signals.length > 0 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.3 }}
          >
            <Box
              sx={{
                p: 2,
                borderRadius: 2,
                border: `1px solid ${alpha(theme.palette.divider, 0.3)}`,
                background: alpha(theme.palette.background.paper, 0.5),
              }}
            >
              <Typography variant="caption" fontWeight={600} color="text.secondary" sx={{ mb: 1, display: "block" }}>
                Top Signals
              </Typography>
              {signals.map((sig, i) => (
                <MiniSignalBar key={sig.name} name={sig.name} score={sig.score} delay={i * 0.08} />
              ))}
            </Box>
          </motion.div>
        )}
      </AnimatePresence>
    </Box>
  );
}
