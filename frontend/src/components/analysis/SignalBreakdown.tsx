import { useState } from "react";
import {
  Box,
  Card,
  Typography,
  LinearProgress,
  Collapse,
  IconButton,
  Chip,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import { motion } from "framer-motion";
import type { SignalScore } from "@/types/analysis";

interface SignalBreakdownProps {
  signals: SignalScore[];
}

function getBarColor(score: number): string {
  if (score <= 0.3) return "#22c55e";
  if (score <= 0.6) return "#f59e0b";
  return "#ef4444";
}

function getCategoryColor(category: string): string {
  switch (category) {
    case "statistical":
      return "#7c3aed";
    case "linguistic":
      return "#06b6d4";
    case "model":
      return "#f59e0b";
    case "structural":
      return "#22c55e";
    default:
      return "#a1a1aa";
  }
}

export default function SignalBreakdown({ signals }: SignalBreakdownProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const sorted = [...signals].sort((a, b) => b.score - a.score);

  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        Signal Breakdown
      </Typography>
      <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
        {sorted.map((signal, index) => {
          const isExpanded = expandedId === signal.name;
          const color = getBarColor(signal.score);

          return (
            <motion.div
              key={signal.name}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.05 }}
            >
              <Card
                sx={{
                  p: 2,
                  cursor: "pointer",
                  "&:hover": { borderColor: "primary.main" },
                }}
                onClick={() =>
                  setExpandedId(isExpanded ? null : signal.name)
                }
              >
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    mb: 1,
                  }}
                >
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                    <Typography variant="body2" fontWeight={600}>
                      {signal.name.replace(/_/g, " ")}
                    </Typography>
                    <Chip
                      label={signal.category}
                      size="small"
                      sx={{
                        backgroundColor: `${getCategoryColor(signal.category)}20`,
                        color: getCategoryColor(signal.category),
                        fontSize: "0.7rem",
                        height: 22,
                      }}
                    />
                  </Box>
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                    <Typography
                      variant="body2"
                      fontWeight={700}
                      sx={{ color }}
                    >
                      {Math.round(signal.score * 100)}%
                    </Typography>
                    <IconButton
                      size="small"
                      sx={{
                        transform: isExpanded ? "rotate(180deg)" : "none",
                        transition: "transform 0.2s",
                      }}
                    >
                      <ExpandMoreIcon fontSize="small" />
                    </IconButton>
                  </Box>
                </Box>

                <LinearProgress
                  variant="determinate"
                  value={signal.score * 100}
                  sx={{
                    height: 6,
                    borderRadius: 3,
                    backgroundColor: "divider",
                    "& .MuiLinearProgress-bar": {
                      backgroundColor: color,
                      borderRadius: 3,
                    },
                  }}
                />

                <Collapse in={isExpanded}>
                  <Box sx={{ mt: 1.5 }}>
                    <Typography variant="caption" color="text.secondary">
                      {signal.description}
                    </Typography>
                    <Typography
                      variant="caption"
                      color="text.secondary"
                      display="block"
                      sx={{ mt: 0.5 }}
                    >
                      Weight: {signal.weight}x
                    </Typography>
                  </Box>
                </Collapse>
              </Card>
            </motion.div>
          );
        })}
      </Box>
    </Box>
  );
}
