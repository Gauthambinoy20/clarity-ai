import { Box, Typography, Chip, useTheme } from "@mui/material";
import { motion } from "framer-motion";

interface ScoreGaugeProps {
  score: number;
  confidence?: number;
  label?: string;
  size?: number;
}

function getScoreColor(score: number): string {
  if (score <= 30) return "#22c55e";
  if (score <= 60) return "#f59e0b";
  return "#ef4444";
}

function getLabel(score: number): string {
  if (score <= 20) return "Human Written";
  if (score <= 40) return "Mostly Human";
  if (score <= 60) return "Uncertain";
  if (score <= 80) return "Likely AI";
  return "AI Generated";
}

export default function ScoreGauge({
  score,
  confidence,
  label,
  size = 220,
}: ScoreGaugeProps) {
  const theme = useTheme();
  const radius = (size - 24) / 2;
  const circumference = 2 * Math.PI * radius * 0.75;
  const strokeDashoffset = circumference - (score / 100) * circumference;
  const color = getScoreColor(score);
  const displayLabel = label || getLabel(score);
  const center = size / 2;
  const strokeWidth = 10;

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 1.5,
      }}
    >
      <Box sx={{ position: "relative", width: size, height: size }}>
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
          {/* Background arc */}
          <circle
            cx={center}
            cy={center}
            r={radius}
            fill="none"
            stroke={theme.palette.divider}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={circumference * 0.25}
            transform={`rotate(135 ${center} ${center})`}
          />
          {/* Animated score arc */}
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
            style={{
              filter: `drop-shadow(0 0 8px ${color}40)`,
            }}
          />
        </svg>

        {/* Center content */}
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
              {Math.round(score)}
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

      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.8 }}
      >
        <Chip
          label={displayLabel}
          sx={{
            backgroundColor: `${color}20`,
            color,
            fontWeight: 600,
            fontSize: "0.85rem",
            px: 1,
          }}
        />
      </motion.div>

      {confidence !== undefined && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1 }}
        >
          <Typography variant="caption" color="text.secondary">
            Confidence: {Math.round(confidence * 100)}%
          </Typography>
        </motion.div>
      )}
    </Box>
  );
}
