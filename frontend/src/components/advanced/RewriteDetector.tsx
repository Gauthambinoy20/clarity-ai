import { useState } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  Alert,
  LinearProgress,
  alpha,
  useTheme,
  Tooltip,
} from "@mui/material";
import AutoFixHighIcon from "@mui/icons-material/AutoFixHigh";
import VerifiedIcon from "@mui/icons-material/Verified";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import { motion } from "framer-motion";

/* ─── Types ──────────────────────────────────────────────────────── */

export interface ResidualPattern {
  id: string;
  pattern: string;
  description: string;
  severity: "high" | "medium" | "low";
  count: number;
}

export interface RewriteDetectionResult {
  isRewritten: boolean;
  naturalnessScore: number;
  confidence: number;
  residualPatterns: ResidualPattern[];
  explanation: string;
}

interface RewriteDetectorProps {
  result: RewriteDetectionResult | null;
  isLoading?: boolean;
}

/* ─── Circular Gauge ─────────────────────────────────────────────── */

function NaturalnessGauge({ score, size = 120 }: { score: number; size?: number }) {
  const theme = useTheme();
  const radius = (size - 16) / 2;
  const circumference = 2 * Math.PI * radius;
  const progress = (score / 100) * circumference;
  const color =
    score >= 70 ? "#22c55e" : score >= 40 ? "#f59e0b" : "#ef4444";

  return (
    <Box sx={{ position: "relative", width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={alpha(theme.palette.divider, 0.15)}
          strokeWidth={8}
        />
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={8}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference - progress}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: circumference - progress }}
          transition={{ duration: 1, ease: "easeOut" }}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
      </svg>
      <Box
        sx={{
          position: "absolute",
          inset: 0,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <Typography variant="h5" fontWeight={800} sx={{ color, lineHeight: 1 }}>
          {score}
        </Typography>
        <Typography variant="caption" color="text.secondary" sx={{ fontSize: "0.65rem" }}>
          Naturalness
        </Typography>
      </Box>
    </Box>
  );
}

/* ─── Severity Chip Colors ───────────────────────────────────────── */

const severityConfig = {
  high: { color: "#ef4444", label: "High" },
  medium: { color: "#f59e0b", label: "Medium" },
  low: { color: "#22c55e", label: "Low" },
};

/* ─── Main Component ─────────────────────────────────────────────── */

export default function RewriteDetector({ result, isLoading }: RewriteDetectorProps) {
  const theme = useTheme();

  if (isLoading) {
    return (
      <Card>
        <CardContent sx={{ p: 3 }}>
          <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 2 }}>
            Analyzing for rewriting patterns...
          </Typography>
          <LinearProgress />
        </CardContent>
      </Card>
    );
  }

  if (!result) return null;

  const badgeColor = result.isRewritten ? "#f59e0b" : "#22c55e";
  const badgeIcon = result.isRewritten ? <AutoFixHighIcon /> : <VerifiedIcon />;
  const badgeLabel = result.isRewritten ? "Rewrite Detected" : "Original Text";

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      <Card
        sx={{
          border: `1px solid ${alpha(badgeColor, 0.3)}`,
          background: `linear-gradient(135deg, ${alpha(badgeColor, 0.04)} 0%, ${alpha(
            theme.palette.background.paper,
            1
          )} 100%)`,
        }}
      >
        <CardContent sx={{ p: 3, "&:last-child": { pb: 3 } }}>
          {/* Header Badge */}
          <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 3 }}>
            <Chip
              icon={badgeIcon}
              label={badgeLabel}
              sx={{
                backgroundColor: alpha(badgeColor, 0.15),
                color: badgeColor,
                fontWeight: 700,
                fontSize: "0.85rem",
                py: 2.5,
                "& .MuiChip-icon": { color: badgeColor },
              }}
            />
            <Tooltip title="Detects if text was AI-generated then paraphrased or humanized">
              <InfoOutlinedIcon sx={{ color: "text.secondary", fontSize: 20 }} />
            </Tooltip>
          </Box>

          {/* Score + Confidence Row */}
          <Box sx={{ display: "flex", alignItems: "center", gap: 4, mb: 3 }}>
            <NaturalnessGauge score={result.naturalnessScore} />

            <Box sx={{ flex: 1 }}>
              <Typography variant="subtitle2" fontWeight={600} sx={{ mb: 1 }}>
                Confidence
              </Typography>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, mb: 0.5 }}>
                <LinearProgress
                  variant="determinate"
                  value={result.confidence * 100}
                  sx={{
                    flex: 1,
                    height: 10,
                    borderRadius: 5,
                    backgroundColor: alpha(theme.palette.primary.main, 0.1),
                    "& .MuiLinearProgress-bar": {
                      borderRadius: 5,
                      background: `linear-gradient(90deg, ${theme.palette.primary.main}, ${theme.palette.secondary.main})`,
                    },
                  }}
                />
                <Typography variant="body2" fontWeight={700}>
                  {Math.round(result.confidence * 100)}%
                </Typography>
              </Box>
              <Typography variant="caption" color="text.secondary">
                How confident the detector is in this classification
              </Typography>
            </Box>
          </Box>

          {/* Residual AI Patterns */}
          {result.residualPatterns.length > 0 && (
            <Box sx={{ mb: 3 }}>
              <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 1.5 }}>
                Residual AI Patterns
              </Typography>
              <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
                {result.residualPatterns.map((p, idx) => {
                  const sev = severityConfig[p.severity];
                  return (
                    <motion.div
                      key={p.id}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: idx * 0.08 }}
                    >
                      <Box
                        sx={{
                          display: "flex",
                          alignItems: "center",
                          gap: 1.5,
                          p: 1.5,
                          borderRadius: 1.5,
                          border: `1px solid ${alpha(sev.color, 0.2)}`,
                          background: alpha(sev.color, 0.04),
                        }}
                      >
                        <WarningAmberIcon sx={{ color: sev.color, fontSize: 18 }} />
                        <Box sx={{ flex: 1, minWidth: 0 }}>
                          <Typography variant="body2" fontWeight={600} noWrap>
                            {p.pattern}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {p.description}
                          </Typography>
                        </Box>
                        <Chip
                          label={sev.label}
                          size="small"
                          sx={{
                            backgroundColor: alpha(sev.color, 0.15),
                            color: sev.color,
                            fontWeight: 600,
                            fontSize: "0.7rem",
                          }}
                        />
                        <Chip
                          label={`x${p.count}`}
                          size="small"
                          variant="outlined"
                          sx={{ fontWeight: 600, fontSize: "0.7rem" }}
                        />
                      </Box>
                    </motion.div>
                  );
                })}
              </Box>
            </Box>
          )}

          {/* Explanation */}
          <Alert
            severity={result.isRewritten ? "warning" : "success"}
            variant="outlined"
            sx={{
              borderRadius: 2,
              "& .MuiAlert-message": { fontSize: "0.85rem" },
            }}
          >
            {result.explanation ||
              (result.isRewritten
                ? "This text appears to have been AI-generated and then paraphrased or humanized to evade detection. Residual patterns from the original AI output are still present."
                : "This text appears to be originally authored without signs of AI-generated rewrites.")}
          </Alert>
        </CardContent>
      </Card>
    </motion.div>
  );
}
