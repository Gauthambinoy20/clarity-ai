import { Box, Card, CardContent, Typography, LinearProgress, Chip } from "@mui/material";
import { motion } from "framer-motion";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface BreakdownItem {
  score: number;
  weight: number;
  weighted_contribution: number;
  description: string;
  [key: string]: unknown;
}

interface OriginalityData {
  originality_score: number;
  category: string;
  breakdown: {
    ai_detection: BreakdownItem;
    plagiarism: BreakdownItem;
    vocabulary_uniqueness: BreakdownItem;
    structural_originality: BreakdownItem;
  };
}

interface OriginalityScoreProps {
  data: OriginalityData;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getScoreColor(score: number): string {
  if (score >= 85) return "#22c55e";
  if (score >= 70) return "#4ade80";
  if (score >= 50) return "#f59e0b";
  if (score >= 30) return "#f97316";
  return "#ef4444";
}

function getCategoryColor(category: string): string {
  switch (category) {
    case "Highly Original":
      return "#22c55e";
    case "Mostly Original":
      return "#4ade80";
    case "Partially Original":
      return "#f59e0b";
    case "Low Originality":
      return "#f97316";
    case "Not Original":
      return "#ef4444";
    default:
      return "#a1a1aa";
  }
}

const BREAKDOWN_LABELS: Record<string, { label: string; color: string }> = {
  ai_detection: { label: "AI Detection", color: "#7c3aed" },
  plagiarism: { label: "Plagiarism", color: "#ef4444" },
  vocabulary_uniqueness: { label: "Vocabulary Uniqueness", color: "#06b6d4" },
  structural_originality: { label: "Structural Originality", color: "#22c55e" },
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function OriginalityScore({ data }: OriginalityScoreProps) {
  const { originality_score, category, breakdown } = data;
  const color = getScoreColor(originality_score);
  const catColor = getCategoryColor(category);

  // SVG gauge parameters
  const size = 200;
  const radius = (size - 20) / 2;
  const circumference = 2 * Math.PI * radius * 0.75;
  const strokeDashoffset = circumference - (originality_score / 100) * circumference;
  const center = size / 2;
  const strokeWidth = 10;

  const breakdownEntries = Object.entries(breakdown) as [string, BreakdownItem][];

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" fontWeight={700} gutterBottom>
          Originality Score
        </Typography>

        {/* Circular Gauge */}
        <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center", mb: 3 }}>
          <Box sx={{ position: "relative", width: size, height: size }}>
            <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
              {/* Background arc */}
              <circle
                cx={center}
                cy={center}
                r={radius}
                fill="none"
                stroke="currentColor"
                strokeWidth={strokeWidth}
                strokeLinecap="round"
                strokeDasharray={circumference}
                strokeDashoffset={circumference * 0.25}
                transform={`rotate(135 ${center} ${center})`}
                opacity={0.1}
              />
              {/* Score arc */}
              <motion.circle
                cx={center}
                cy={center}
                r={radius}
                fill="none"
                stroke={color}
                strokeWidth={strokeWidth}
                strokeLinecap="round"
                strokeDasharray={circumference}
                initial={{ strokeDashoffset: circumference }}
                animate={{ strokeDashoffset }}
                transition={{ duration: 1.5, ease: "easeOut" }}
                transform={`rotate(135 ${center} ${center})`}
                style={{ filter: `drop-shadow(0 0 8px ${color}40)` }}
              />
            </svg>

            {/* Center text */}
            <Box
              sx={{
                position: "absolute",
                top: "50%",
                left: "50%",
                transform: "translate(-50%, -45%)",
                textAlign: "center",
              }}
            >
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ delay: 0.5, type: "spring", stiffness: 200 }}
              >
                <Typography
                  variant="h2"
                  fontWeight={800}
                  sx={{ color, lineHeight: 1, fontSize: size * 0.22 }}
                >
                  {Math.round(originality_score)}
                </Typography>
                <Typography
                  variant="caption"
                  color="text.secondary"
                  fontWeight={500}
                  sx={{ fontSize: size * 0.06 }}
                >
                  / 100
                </Typography>
              </motion.div>
            </Box>
          </Box>

          {/* Category Badge */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.8 }}
          >
            <Chip
              label={category}
              sx={{
                mt: 1,
                fontWeight: 700,
                fontSize: "0.85rem",
                px: 2,
                backgroundColor: `${catColor}20`,
                color: catColor,
              }}
            />
          </motion.div>
        </Box>

        {/* Breakdown */}
        <Typography variant="subtitle2" fontWeight={600} sx={{ mb: 2 }}>
          Score Breakdown
        </Typography>

        <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
          {breakdownEntries.map(([key, item], index) => {
            const meta = BREAKDOWN_LABELS[key] || { label: key, color: "#a1a1aa" };
            return (
              <motion.div
                key={key}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.3 + index * 0.1 }}
              >
                <Box>
                  <Box
                    sx={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      mb: 0.5,
                    }}
                  >
                    <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                      <Box
                        sx={{
                          width: 10,
                          height: 10,
                          borderRadius: "50%",
                          backgroundColor: meta.color,
                        }}
                      />
                      <Typography variant="body2" fontWeight={500}>
                        {meta.label}
                      </Typography>
                      <Chip
                        label={`${Math.round(item.weight * 100)}%`}
                        size="small"
                        variant="outlined"
                        sx={{ height: 20, fontSize: "0.65rem" }}
                      />
                    </Box>
                    <Typography variant="body2" fontWeight={700} sx={{ color: meta.color }}>
                      {Math.round(item.score)}
                    </Typography>
                  </Box>

                  <LinearProgress
                    variant="determinate"
                    value={Math.min(item.score, 100)}
                    sx={{
                      height: 6,
                      borderRadius: 3,
                      backgroundColor: "divider",
                      "& .MuiLinearProgress-bar": {
                        backgroundColor: meta.color,
                        borderRadius: 3,
                      },
                    }}
                  />

                  <Typography variant="caption" color="text.secondary" sx={{ mt: 0.25, display: "block" }}>
                    {item.description} (contributes {item.weighted_contribution.toFixed(1)} pts)
                  </Typography>
                </Box>
              </motion.div>
            );
          })}
        </Box>
      </CardContent>
    </Card>
  );
}
