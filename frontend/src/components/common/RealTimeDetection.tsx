import { useState, useEffect, useRef, useCallback } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  LinearProgress,
  Chip,
  Button,
  TextField,
  Alert,
} from "@mui/material";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import StopIcon from "@mui/icons-material/Stop";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutline";
import HourglassEmptyIcon from "@mui/icons-material/HourglassEmpty";
import { motion, AnimatePresence } from "framer-motion";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface SignalResult {
  signal: string;
  status: "completed" | "error";
  result: {
    signal: string;
    ai_probability: number;
    confidence: string;
    error?: string;
    [key: string]: unknown;
  };
}

interface ProgressUpdate {
  progress: number;
  total: number;
  current_signal: string;
}

interface FinalResult {
  status: "complete";
  overall_score: number;
  classification: string;
  total_signals: number;
  processing_time_ms: number;
  word_count: number;
}

type WSMessage = SignalResult | ProgressUpdate | FinalResult | { status: string; message?: string; total_signals?: number };

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getSignalColor(probability: number): string {
  if (probability <= 0.3) return "#22c55e";
  if (probability <= 0.6) return "#f59e0b";
  return "#ef4444";
}

function getClassificationColor(classification: string): string {
  switch (classification) {
    case "human_written":
      return "#22c55e";
    case "mixed":
      return "#f59e0b";
    case "ai_generated":
      return "#ef4444";
    default:
      return "#a1a1aa";
  }
}

function formatSignalName(name: string): string {
  return name
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function RealTimeDetection() {
  const [text, setText] = useState("");
  const [isConnected, setIsConnected] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [signals, setSignals] = useState<SignalResult[]>([]);
  const [progress, setProgress] = useState<ProgressUpdate | null>(null);
  const [finalResult, setFinalResult] = useState<FinalResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const connect = useCallback(() => {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    const ws = new WebSocket(`${protocol}//${host}/ws/detect`);

    ws.onopen = () => {
      setIsConnected(true);
      setError(null);
    };

    ws.onclose = () => {
      setIsConnected(false);
      setIsAnalyzing(false);
    };

    ws.onerror = () => {
      setError("WebSocket connection failed. Is the server running?");
      setIsConnected(false);
      setIsAnalyzing(false);
    };

    ws.onmessage = (event) => {
      try {
        const data: WSMessage = JSON.parse(event.data);

        if ("status" in data && data.status === "error") {
          setError((data as { message?: string }).message || "Unknown error");
          setIsAnalyzing(false);
          return;
        }

        if ("status" in data && data.status === "started") {
          setSignals([]);
          setProgress(null);
          setFinalResult(null);
          setError(null);
          return;
        }

        // Progress update
        if ("progress" in data && "total" in data && "current_signal" in data) {
          setProgress(data as ProgressUpdate);
          return;
        }

        // Signal result
        if ("signal" in data && "result" in data) {
          setSignals((prev) => [...prev, data as SignalResult]);
          return;
        }

        // Final result
        if ("status" in data && data.status === "complete") {
          setFinalResult(data as FinalResult);
          setIsAnalyzing(false);
          return;
        }
      } catch {
        // Ignore parse errors
      }
    };

    wsRef.current = ws;
  }, []);

  useEffect(() => {
    connect();
    return () => {
      wsRef.current?.close();
    };
  }, [connect]);

  const handleAnalyze = () => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      setError("Not connected to server.");
      return;
    }
    if (!text.trim()) {
      setError("Please enter some text to analyze.");
      return;
    }

    setIsAnalyzing(true);
    setSignals([]);
    setProgress(null);
    setFinalResult(null);
    setError(null);

    wsRef.current.send(JSON.stringify({ text: text.trim() }));
  };

  const handleStop = () => {
    wsRef.current?.close();
    setIsAnalyzing(false);
    connect();
  };

  const totalSignals = progress?.total || 14;
  const completedCount = signals.length;
  const progressPercent = (completedCount / totalSignals) * 100;

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
      {/* Header */}
      <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
        <Typography variant="h5" fontWeight={700}>
          Real-Time Detection
        </Typography>
        <Chip
          label={isConnected ? "Connected" : "Disconnected"}
          size="small"
          color={isConnected ? "success" : "error"}
          variant="outlined"
        />
      </Box>

      {error && (
        <Alert severity="error" onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Text Input */}
      <TextField
        multiline
        minRows={4}
        maxRows={12}
        placeholder="Paste text here for real-time AI detection..."
        value={text}
        onChange={(e) => setText(e.target.value)}
        disabled={isAnalyzing}
        fullWidth
      />

      {/* Action Buttons */}
      <Box sx={{ display: "flex", gap: 2 }}>
        <Button
          variant="contained"
          startIcon={<PlayArrowIcon />}
          onClick={handleAnalyze}
          disabled={isAnalyzing || !isConnected || !text.trim()}
          sx={{
            background: "linear-gradient(135deg, #7c3aed, #06b6d4)",
            "&:hover": { background: "linear-gradient(135deg, #6d28d9, #0891b2)" },
          }}
        >
          Analyze
        </Button>
        {isAnalyzing && (
          <Button
            variant="outlined"
            color="error"
            startIcon={<StopIcon />}
            onClick={handleStop}
          >
            Stop
          </Button>
        )}
      </Box>

      {/* Progress Bar */}
      {(isAnalyzing || signals.length > 0) && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          <Card>
            <CardContent>
              <Box sx={{ display: "flex", justifyContent: "space-between", mb: 1 }}>
                <Typography variant="body2" fontWeight={600}>
                  {isAnalyzing
                    ? `${completedCount}/${totalSignals} signals complete`
                    : `All ${completedCount} signals complete`}
                </Typography>
                {progress && isAnalyzing && (
                  <Typography variant="caption" color="text.secondary">
                    Analyzing: {formatSignalName(progress.current_signal)}
                  </Typography>
                )}
              </Box>
              <LinearProgress
                variant="determinate"
                value={progressPercent}
                sx={{
                  height: 8,
                  borderRadius: 4,
                  backgroundColor: "divider",
                  "& .MuiLinearProgress-bar": {
                    background: "linear-gradient(90deg, #7c3aed, #06b6d4)",
                    borderRadius: 4,
                  },
                }}
              />
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* Signal Cards */}
      <AnimatePresence>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
          {signals.map((sig, index) => {
            const prob = sig.result.ai_probability;
            const color = getSignalColor(prob);
            const isError = sig.status === "error";

            return (
              <motion.div
                key={sig.signal + index}
                initial={{ opacity: 0, x: -30, scale: 0.95 }}
                animate={{ opacity: 1, x: 0, scale: 1 }}
                transition={{
                  duration: 0.4,
                  delay: 0.05,
                  type: "spring",
                  stiffness: 200,
                  damping: 20,
                }}
              >
                <Card
                  sx={{
                    borderLeft: `4px solid ${isError ? "#ef4444" : color}`,
                  }}
                >
                  <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
                    <Box
                      sx={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                      }}
                    >
                      <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
                        {isError ? (
                          <ErrorOutlineIcon sx={{ color: "#ef4444", fontSize: 20 }} />
                        ) : (
                          <CheckCircleOutlineIcon sx={{ color, fontSize: 20 }} />
                        )}
                        <Typography variant="body2" fontWeight={600}>
                          {formatSignalName(sig.signal)}
                        </Typography>
                        <Chip
                          label={sig.result.confidence}
                          size="small"
                          sx={{
                            height: 20,
                            fontSize: "0.65rem",
                            backgroundColor: `${color}20`,
                            color,
                          }}
                        />
                      </Box>
                      <Typography
                        variant="body1"
                        fontWeight={700}
                        sx={{ color }}
                      >
                        {isError ? "ERR" : `${Math.round(prob * 100)}%`}
                      </Typography>
                    </Box>

                    {!isError && (
                      <LinearProgress
                        variant="determinate"
                        value={prob * 100}
                        sx={{
                          mt: 1,
                          height: 4,
                          borderRadius: 2,
                          backgroundColor: "divider",
                          "& .MuiLinearProgress-bar": {
                            backgroundColor: color,
                            borderRadius: 2,
                          },
                        }}
                      />
                    )}
                  </CardContent>
                </Card>
              </motion.div>
            );
          })}
        </Box>
      </AnimatePresence>

      {/* Waiting indicator */}
      {isAnalyzing && signals.length === 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
        >
          <Box sx={{ display: "flex", alignItems: "center", gap: 1, justifyContent: "center", py: 3 }}>
            <HourglassEmptyIcon color="action" />
            <Typography variant="body2" color="text.secondary">
              Starting analysis...
            </Typography>
          </Box>
        </motion.div>
      )}

      {/* Final Score */}
      <AnimatePresence>
        {finalResult && (
          <motion.div
            initial={{ opacity: 0, scale: 0.9, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            transition={{
              duration: 0.6,
              type: "spring",
              stiffness: 150,
              damping: 15,
            }}
          >
            <Card
              sx={{
                background: "linear-gradient(135deg, #7c3aed15, #06b6d415)",
                border: "2px solid",
                borderColor: getClassificationColor(finalResult.classification),
              }}
            >
              <CardContent>
                <Box sx={{ textAlign: "center", py: 2 }}>
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ delay: 0.2, type: "spring", stiffness: 200 }}
                  >
                    <Typography
                      variant="h2"
                      fontWeight={800}
                      sx={{
                        color: getClassificationColor(finalResult.classification),
                        lineHeight: 1,
                      }}
                    >
                      {Math.round(finalResult.overall_score * 100)}%
                    </Typography>
                  </motion.div>
                  <Typography variant="body1" color="text.secondary" sx={{ mt: 1 }}>
                    AI Probability
                  </Typography>
                  <Chip
                    label={finalResult.classification.replace(/_/g, " ").toUpperCase()}
                    sx={{
                      mt: 1.5,
                      fontWeight: 700,
                      backgroundColor: `${getClassificationColor(finalResult.classification)}20`,
                      color: getClassificationColor(finalResult.classification),
                    }}
                  />
                  <Box sx={{ mt: 2, display: "flex", justifyContent: "center", gap: 3 }}>
                    <Typography variant="caption" color="text.secondary">
                      {finalResult.word_count} words
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {finalResult.total_signals} signals
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {finalResult.processing_time_ms}ms
                    </Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>
    </Box>
  );
}
