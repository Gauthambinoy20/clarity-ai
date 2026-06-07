import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  LinearProgress,
  useTheme,
} from "@mui/material";
import Grid from "@mui/material/Grid2";
import { motion } from "framer-motion";
import type { ToneResult } from "@/types/analytics";

interface ToneAnalyzerProps {
  data: ToneResult;
}

function AnimatedBar({
  label,
  value,
  color,
  delay = 0,
}: {
  label: string;
  value: number;
  color: string;
  delay?: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay, duration: 0.4 }}
    >
      <Box sx={{ mb: 2 }}>
        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            mb: 0.5,
          }}
        >
          <Typography variant="body2" fontWeight={500}>
            {label}
          </Typography>
          <Typography variant="body2" fontWeight={600} sx={{ color }}>
            {(value * 100).toFixed(0)}%
          </Typography>
        </Box>
        <LinearProgress
          variant="determinate"
          value={value * 100}
          sx={{
            height: 10,
            borderRadius: 5,
            backgroundColor: "action.hover",
            "& .MuiLinearProgress-bar": {
              borderRadius: 5,
              backgroundColor: color,
            },
          }}
        />
      </Box>
    </motion.div>
  );
}

function SentimentGauge({ value }: { value: number }) {
  const theme = useTheme();
  const normalized = (value + 1) / 2;
  const percentage = normalized * 100;

  const getColor = () => {
    if (value > 0.3) return theme.palette.success.main;
    if (value < -0.3) return theme.palette.error.main;
    return theme.palette.warning.main;
  };

  const getLabel = () => {
    if (value > 0.5) return "Very Positive";
    if (value > 0.15) return "Positive";
    if (value > -0.15) return "Neutral";
    if (value > -0.5) return "Negative";
    return "Very Negative";
  };

  return (
    <Box sx={{ textAlign: "center" }}>
      <Typography variant="overline" color="text.secondary">
        Sentiment
      </Typography>
      <Box sx={{ position: "relative", mt: 1, mb: 1 }}>
        <Box
          sx={{
            height: 12,
            borderRadius: 6,
            background: `linear-gradient(to right, ${theme.palette.error.main}, ${theme.palette.warning.main}, ${theme.palette.success.main})`,
            position: "relative",
          }}
        >
          <motion.div
            initial={{ left: "50%" }}
            animate={{ left: `${percentage}%` }}
            transition={{ duration: 0.8, ease: "easeOut" }}
            style={{
              position: "absolute",
              top: -4,
              width: 20,
              height: 20,
              borderRadius: "50%",
              backgroundColor: getColor(),
              border: `3px solid ${theme.palette.background.paper}`,
              transform: "translateX(-50%)",
              boxShadow: "0 2px 8px rgba(0,0,0,0.3)",
            }}
          />
        </Box>
        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            mt: 0.5,
          }}
        >
          <Typography variant="caption" color="text.secondary">
            Negative
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Neutral
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Positive
          </Typography>
        </Box>
      </Box>
      <Chip
        label={getLabel()}
        size="small"
        sx={{
          mt: 1,
          fontWeight: 600,
          backgroundColor: getColor(),
          color: "#fff",
        }}
      />
    </Box>
  );
}

const emotionColors: Record<string, string> = {
  joy: "#22c55e",
  happiness: "#22c55e",
  sadness: "#3b82f6",
  anger: "#ef4444",
  fear: "#8b5cf6",
  surprise: "#f59e0b",
  disgust: "#84cc16",
  trust: "#06b6d4",
  anticipation: "#f97316",
  love: "#ec4899",
  optimism: "#10b981",
  pessimism: "#6366f1",
  neutral: "#71717a",
};

export default function ToneAnalyzer({ data }: ToneAnalyzerProps) {
  const theme = useTheme();

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
        <Grid container spacing={2}>
          {/* Sentiment Gauge */}
          <Grid size={{ xs: 12, md: 6 }}>
            <Card sx={{ height: "100%" }}>
              <CardContent sx={{ p: 3 }}>
                <SentimentGauge value={data.sentiment} />
              </CardContent>
            </Card>
          </Grid>

          {/* Emotions */}
          <Grid size={{ xs: 12, md: 6 }}>
            <Card sx={{ height: "100%" }}>
              <CardContent sx={{ p: 3 }}>
                <Typography variant="overline" color="text.secondary">
                  Detected Emotions
                </Typography>
                <Box
                  sx={{
                    display: "flex",
                    flexWrap: "wrap",
                    gap: 1,
                    mt: 1.5,
                  }}
                >
                  {data.emotions.map((em, i) => (
                    <motion.div
                      key={em.emotion}
                      initial={{ opacity: 0, scale: 0.7 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ delay: i * 0.05, duration: 0.3 }}
                    >
                      <Chip
                        label={`${em.emotion} ${(em.score * 100).toFixed(0)}%`}
                        sx={{
                          fontWeight: 600,
                          backgroundColor:
                            emotionColors[em.emotion.toLowerCase()] ||
                            theme.palette.primary.main,
                          color: "#fff",
                          opacity: 0.5 + em.score * 0.5,
                        }}
                      />
                    </motion.div>
                  ))}
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        {/* Tone Metrics */}
        <Card>
          <CardContent sx={{ p: 3 }}>
            <Typography variant="subtitle2" fontWeight={600} gutterBottom>
              Tone Metrics
            </Typography>
            <Box sx={{ mt: 2 }}>
              <AnimatedBar
                label="Formality"
                value={data.formality}
                color={theme.palette.primary.main}
                delay={0}
              />
              <AnimatedBar
                label="Objectivity"
                value={data.objectivity}
                color={theme.palette.secondary.main}
                delay={0.1}
              />
              <AnimatedBar
                label="Persuasiveness"
                value={data.persuasiveness}
                color={theme.palette.warning.main}
                delay={0.2}
              />
              <AnimatedBar
                label="Urgency"
                value={data.urgency}
                color={theme.palette.error.main}
                delay={0.3}
              />
              <AnimatedBar
                label="Confidence"
                value={data.confidence}
                color={theme.palette.success.main}
                delay={0.4}
              />
            </Box>
          </CardContent>
        </Card>

        {/* Professional / Casual Slider */}
        <Card>
          <CardContent sx={{ p: 3 }}>
            <Typography variant="subtitle2" fontWeight={600} gutterBottom>
              Writing Style Spectrum
            </Typography>
            <Box sx={{ mt: 2 }}>
              <Box
                sx={{
                  display: "flex",
                  justifyContent: "space-between",
                  mb: 0.5,
                }}
              >
                <Typography variant="caption" fontWeight={600} color="secondary.main">
                  Casual
                </Typography>
                <Typography variant="caption" fontWeight={600} color="primary.main">
                  Formal
                </Typography>
              </Box>
              <Box
                sx={{
                  height: 14,
                  borderRadius: 7,
                  background: `linear-gradient(to right, ${theme.palette.secondary.main}, ${theme.palette.primary.main})`,
                  position: "relative",
                }}
              >
                <motion.div
                  initial={{ left: "50%" }}
                  animate={{ left: `${data.formality * 100}%` }}
                  transition={{ duration: 0.8, ease: "easeOut" }}
                  style={{
                    position: "absolute",
                    top: -5,
                    width: 24,
                    height: 24,
                    borderRadius: "50%",
                    backgroundColor: theme.palette.background.paper,
                    border: `3px solid ${theme.palette.primary.main}`,
                    transform: "translateX(-50%)",
                    boxShadow: "0 2px 8px rgba(0,0,0,0.2)",
                  }}
                />
              </Box>
            </Box>
          </CardContent>
        </Card>
      </Box>
    </motion.div>
  );
}
