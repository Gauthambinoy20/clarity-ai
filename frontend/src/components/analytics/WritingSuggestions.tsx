import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Alert,
  useTheme,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import LightbulbOutlinedIcon from "@mui/icons-material/LightbulbOutlined";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import { motion } from "framer-motion";
import type { WritingSuggestionsResult, WritingSuggestion } from "@/types/analytics";

interface WritingSuggestionsProps {
  data: WritingSuggestionsResult;
}

const categoryConfig: Record<
  string,
  { label: string; color: string; icon: string }
> = {
  clarity: { label: "Clarity", color: "#7c3aed", icon: "visibility" },
  conciseness: { label: "Conciseness", color: "#06b6d4", icon: "compress" },
  engagement: { label: "Engagement", color: "#22c55e", icon: "thumb_up" },
  vocabulary: { label: "Vocabulary", color: "#f59e0b", icon: "menu_book" },
  structure: { label: "Structure", color: "#ef4444", icon: "account_tree" },
};

const severityColors: Record<string, string> = {
  high: "#ef4444",
  medium: "#f59e0b",
  low: "#3b82f6",
};

function ScoreGauge({ score, delay = 0 }: { score: number; delay?: number }) {
  const theme = useTheme();
  const size = 140;
  const strokeWidth = 12;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference * (1 - score / 100);

  const getColor = () => {
    if (score >= 80) return theme.palette.success.main;
    if (score >= 60) return theme.palette.warning.main;
    return theme.palette.error.main;
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ delay, duration: 0.5 }}
    >
      <Box sx={{ textAlign: "center" }}>
        <Box sx={{ position: "relative", display: "inline-block" }}>
          <svg width={size} height={size}>
            <circle
              cx={size / 2}
              cy={size / 2}
              r={radius}
              fill="none"
              stroke={theme.palette.divider}
              strokeWidth={strokeWidth}
            />
            <motion.circle
              cx={size / 2}
              cy={size / 2}
              r={radius}
              fill="none"
              stroke={getColor()}
              strokeWidth={strokeWidth}
              strokeLinecap="round"
              strokeDasharray={circumference}
              initial={{ strokeDashoffset: circumference }}
              animate={{ strokeDashoffset }}
              transition={{ delay: delay + 0.2, duration: 1, ease: "easeOut" }}
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
            <Typography variant="h4" fontWeight={800}>
              {score}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              / 100
            </Typography>
          </Box>
        </Box>
        <Typography variant="subtitle2" fontWeight={600} sx={{ mt: 1 }}>
          Overall Writing Score
        </Typography>
      </Box>
    </motion.div>
  );
}

function SuggestionCard({
  suggestion,
  index,
}: {
  suggestion: WritingSuggestion;
  index: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.05, duration: 0.3 }}
    >
      <Box
        sx={{
          p: 2,
          mb: 1.5,
          borderRadius: 2,
          backgroundColor: "action.hover",
          border: "1px solid",
          borderColor: "divider",
        }}
      >
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 1,
            mb: 1,
          }}
        >
          <LightbulbOutlinedIcon
            sx={{ fontSize: 18, color: severityColors[suggestion.severity] }}
          />
          <Typography variant="body2" fontWeight={600} sx={{ flex: 1 }}>
            {suggestion.message}
          </Typography>
          <Chip
            label={suggestion.severity}
            size="small"
            sx={{
              backgroundColor: severityColors[suggestion.severity],
              color: "#fff",
              fontWeight: 600,
              fontSize: "0.65rem",
              height: 22,
              textTransform: "capitalize",
            }}
          />
        </Box>

        {suggestion.original && (
          <Box sx={{ ml: 3.5, display: "flex", flexDirection: "column", gap: 0.5 }}>
            <Typography
              variant="body2"
              sx={{
                px: 1.5,
                py: 0.5,
                borderRadius: 1,
                backgroundColor: "rgba(239,68,68,0.1)",
                borderLeft: "3px solid",
                borderColor: "error.main",
                fontFamily: "monospace",
                fontSize: "0.85rem",
                textDecoration: "line-through",
              }}
            >
              {suggestion.original}
            </Typography>
            {suggestion.suggested && (
              <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                <ArrowForwardIcon
                  sx={{ fontSize: 14, color: "success.main" }}
                />
                <Typography
                  variant="body2"
                  sx={{
                    px: 1.5,
                    py: 0.5,
                    borderRadius: 1,
                    backgroundColor: "rgba(34,197,94,0.1)",
                    borderLeft: "3px solid",
                    borderColor: "success.main",
                    fontFamily: "monospace",
                    fontSize: "0.85rem",
                    flex: 1,
                  }}
                >
                  {suggestion.suggested}
                </Typography>
              </Box>
            )}
          </Box>
        )}

        {suggestion.explanation && (
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ display: "block", mt: 1, ml: 3.5 }}
          >
            {suggestion.explanation}
          </Typography>
        )}
      </Box>
    </motion.div>
  );
}

export default function WritingSuggestions({ data }: WritingSuggestionsProps) {
  const grouped = data.suggestions.reduce<Record<string, WritingSuggestion[]>>(
    (acc, s) => {
      if (!acc[s.category]) acc[s.category] = [];
      acc[s.category].push(s);
      return acc;
    },
    {}
  );

  const categories = Object.keys(categoryConfig);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
        {/* Overall score */}
        <Card>
          <CardContent sx={{ py: 4 }}>
            <ScoreGauge score={data.overall_score} />

            {/* Category scores */}
            <Box
              sx={{
                display: "flex",
                justifyContent: "center",
                gap: 2,
                mt: 3,
                flexWrap: "wrap",
              }}
            >
              {Object.entries(data.category_scores).map(([cat, score]) => {
                const config = categoryConfig[cat];
                return (
                  <Chip
                    key={cat}
                    label={`${config?.label || cat}: ${score}/100`}
                    sx={{
                      fontWeight: 600,
                      borderColor: config?.color || "#7c3aed",
                      color: config?.color || "#7c3aed",
                    }}
                    variant="outlined"
                  />
                );
              })}
            </Box>
          </CardContent>
        </Card>

        {/* Suggestions by category */}
        {data.suggestions.length === 0 ? (
          <Alert severity="success" sx={{ borderRadius: 2 }}>
            Your writing looks excellent! No suggestions at this time.
          </Alert>
        ) : (
          categories
            .filter((cat) => grouped[cat]?.length)
            .map((cat) => {
              const config = categoryConfig[cat];
              const suggestions = grouped[cat];
              return (
                <Accordion
                  key={cat}
                  defaultExpanded
                  sx={{
                    borderRadius: "16px !important",
                    "&:before": { display: "none" },
                    border: "1px solid",
                    borderColor: "divider",
                    overflow: "hidden",
                  }}
                >
                  <AccordionSummary
                    expandIcon={<ExpandMoreIcon />}
                    sx={{ px: 3 }}
                  >
                    <Box
                      sx={{
                        display: "flex",
                        alignItems: "center",
                        gap: 1.5,
                      }}
                    >
                      <Box
                        sx={{
                          width: 8,
                          height: 8,
                          borderRadius: "50%",
                          backgroundColor: config.color,
                        }}
                      />
                      <Typography variant="subtitle2" fontWeight={600}>
                        {config.label}
                      </Typography>
                      <Chip
                        label={`${suggestions.length} suggestion${suggestions.length !== 1 ? "s" : ""}`}
                        size="small"
                        variant="outlined"
                        sx={{ fontWeight: 500, height: 22, fontSize: "0.7rem" }}
                      />
                    </Box>
                  </AccordionSummary>
                  <AccordionDetails sx={{ px: 3, pt: 0 }}>
                    {suggestions.map((s, i) => (
                      <SuggestionCard key={s.id} suggestion={s} index={i} />
                    ))}
                  </AccordionDetails>
                </Accordion>
              );
            })
        )}
      </Box>
    </motion.div>
  );
}
