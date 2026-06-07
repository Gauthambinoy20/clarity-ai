import { useState } from "react";
import {
  Box,
  Typography,
  Popover,
  Card,
  CardContent,
  LinearProgress,
} from "@mui/material";
import { motion } from "framer-motion";
import type { SentenceScore } from "@/types/analysis";

interface SentenceHeatmapProps {
  sentences: SentenceScore[];
}

function getHeatColor(score: number): string {
  if (score <= 0.3) return "#22c55e";
  if (score <= 0.5) return "#84cc16";
  if (score <= 0.6) return "#f59e0b";
  if (score <= 0.8) return "#f97316";
  return "#ef4444";
}

export default function SentenceHeatmap({ sentences }: SentenceHeatmapProps) {
  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null);
  const [selected, setSelected] = useState<SentenceScore | null>(null);

  const handleClick = (
    event: React.MouseEvent<HTMLElement>,
    sentence: SentenceScore
  ) => {
    setAnchorEl(event.currentTarget);
    setSelected(sentence);
  };

  const handleClose = () => {
    setAnchorEl(null);
    setSelected(null);
  };

  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        Sentence Heatmap
      </Typography>
      <Typography variant="caption" color="text.secondary" gutterBottom display="block" sx={{ mb: 2 }}>
        Click any sentence for detailed scores. Green = human, Red = AI.
      </Typography>

      <Box
        sx={{
          lineHeight: 2.2,
          fontSize: "0.95rem",
        }}
      >
        {sentences.map((sentence, index) => {
          const color = getHeatColor(sentence.score);
          return (
            <motion.span
              key={index}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: index * 0.02 }}
              style={{
                backgroundColor: `${color}25`,
                borderBottom: `2px solid ${color}`,
                padding: "2px 4px",
                borderRadius: 4,
                cursor: "pointer",
                marginRight: 4,
                display: "inline",
                transition: "background-color 0.2s",
              }}
              whileHover={{
                backgroundColor: `${color}45`,
              }}
              onClick={(e: React.MouseEvent<HTMLElement>) =>
                handleClick(e, sentence)
              }
            >
              {sentence.text}
            </motion.span>
          );
        })}
      </Box>

      <Popover
        open={Boolean(anchorEl)}
        anchorEl={anchorEl}
        onClose={handleClose}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
        transformOrigin={{ vertical: "top", horizontal: "center" }}
        slotProps={{
          paper: {
            sx: { borderRadius: 2, maxWidth: 360 },
          },
        }}
      >
        {selected && (
          <Card sx={{ border: "none" }}>
            <CardContent>
              <Typography variant="body2" fontWeight={500} gutterBottom>
                AI Probability:{" "}
                <span style={{ color: getHeatColor(selected.score) }}>
                  {Math.round(selected.score * 100)}%
                </span>
              </Typography>

              <Box sx={{ mt: 1.5 }}>
                {Object.entries(selected.signals).map(([name, value]) => (
                  <Box key={name} sx={{ mb: 1 }}>
                    <Box
                      sx={{
                        display: "flex",
                        justifyContent: "space-between",
                        mb: 0.25,
                      }}
                    >
                      <Typography variant="caption" color="text.secondary">
                        {name.replace(/_/g, " ")}
                      </Typography>
                      <Typography variant="caption" fontWeight={600}>
                        {Math.round(value * 100)}%
                      </Typography>
                    </Box>
                    <LinearProgress
                      variant="determinate"
                      value={value * 100}
                      sx={{
                        height: 4,
                        borderRadius: 2,
                        backgroundColor: "divider",
                        "& .MuiLinearProgress-bar": {
                          backgroundColor: getHeatColor(value),
                          borderRadius: 2,
                        },
                      }}
                    />
                  </Box>
                ))}
              </Box>
            </CardContent>
          </Card>
        )}
      </Popover>
    </Box>
  );
}
