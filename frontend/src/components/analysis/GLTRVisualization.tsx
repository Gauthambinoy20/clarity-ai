import { Box, Typography, Tooltip, Chip } from "@mui/material";
import { motion } from "framer-motion";
import type { GLTRToken } from "@/types/analysis";

interface GLTRVisualizationProps {
  tokens: GLTRToken[];
}

const categoryConfig: Record<
  string,
  { color: string; label: string; bg: string }
> = {
  top10: { color: "#22c55e", label: "Top 10", bg: "#22c55e30" },
  top100: { color: "#f59e0b", label: "Top 100", bg: "#f59e0b30" },
  top1000: { color: "#ef4444", label: "Top 1000", bg: "#ef444430" },
  rare: { color: "#a855f7", label: "Rare (1000+)", bg: "#a855f730" },
};

export default function GLTRVisualization({ tokens }: GLTRVisualizationProps) {
  // Category stats
  const stats = tokens.reduce(
    (acc, t) => {
      acc[t.category] = (acc[t.category] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>
  );

  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        GLTR Token Analysis
      </Typography>

      {/* Legend */}
      <Box sx={{ display: "flex", gap: 1.5, mb: 2, flexWrap: "wrap" }}>
        {Object.entries(categoryConfig).map(([key, config]) => (
          <Chip
            key={key}
            label={`${config.label}: ${stats[key] || 0}`}
            size="small"
            sx={{
              backgroundColor: config.bg,
              color: config.color,
              fontWeight: 600,
              fontSize: "0.75rem",
            }}
          />
        ))}
      </Box>

      <Typography variant="caption" color="text.secondary" gutterBottom display="block" sx={{ mb: 2 }}>
        AI-generated text tends to favor top-ranked tokens (green). More rare
        tokens (purple) suggests human writing.
      </Typography>

      {/* Token display */}
      <Box
        sx={{
          lineHeight: 2.4,
          fontSize: "0.9rem",
          fontFamily: "'Inter', monospace",
        }}
      >
        {tokens.map((token, index) => {
          const config = categoryConfig[token.category];
          return (
            <Tooltip
              key={index}
              title={
                <Box sx={{ p: 0.5 }}>
                  <Typography variant="caption" display="block" fontWeight={600}>
                    &quot;{token.token}&quot;
                  </Typography>
                  <Typography variant="caption" display="block">
                    Rank: #{token.rank}
                  </Typography>
                  <Typography variant="caption" display="block">
                    Probability: {(token.probability * 100).toFixed(2)}%
                  </Typography>
                  <Typography variant="caption" display="block">
                    Entropy: {token.entropy.toFixed(3)}
                  </Typography>
                </Box>
              }
              arrow
              placement="top"
            >
              <motion.span
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: index * 0.005 }}
                style={{
                  backgroundColor: config.bg,
                  color: config.color,
                  padding: "2px 5px",
                  borderRadius: 4,
                  cursor: "pointer",
                  marginRight: 2,
                  display: "inline-block",
                  fontWeight: 500,
                }}
              >
                {token.token}
              </motion.span>
            </Tooltip>
          );
        })}
      </Box>
    </Box>
  );
}
