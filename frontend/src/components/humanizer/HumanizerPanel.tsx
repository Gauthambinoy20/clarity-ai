import {
  Box,
  Card,
  CardContent,
  Typography,
  ToggleButtonGroup,
  ToggleButton,
  Chip,
  LinearProgress,
  Divider,
  useTheme,
} from "@mui/material";
import Grid from "@mui/material/Grid2";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import { motion } from "framer-motion";
import type { HumanizationResult } from "@/types/analysis";

interface HumanizerPanelProps {
  result: HumanizationResult;
  style: string;
  onStyleChange: (style: string) => void;
}

export default function HumanizerPanel({
  result,
  style,
  onStyleChange,
}: HumanizerPanelProps) {
  const theme = useTheme();

  const scoreDrop = result.originalScore - result.humanizedScore;
  const scoreDropColor =
    scoreDrop > 40 ? "#22c55e" : scoreDrop > 20 ? "#f59e0b" : "#ef4444";

  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
        {/* Style selector */}
        <Card>
          <CardContent>
            <Typography variant="subtitle2" color="text.secondary" gutterBottom>
              Writing Style
            </Typography>
            <ToggleButtonGroup
              value={style}
              exclusive
              onChange={(_, v) => v && onStyleChange(v)}
              size="small"
              sx={{ flexWrap: "wrap" }}
            >
              <ToggleButton value="academic">Academic</ToggleButton>
              <ToggleButton value="casual">Casual</ToggleButton>
              <ToggleButton value="professional">Professional</ToggleButton>
              <ToggleButton value="creative">Creative</ToggleButton>
              <ToggleButton value="journalistic">Journalistic</ToggleButton>
            </ToggleButtonGroup>
          </CardContent>
        </Card>

        {/* Score summary */}
        <Grid container spacing={2}>
          <Grid size={{ xs: 12, sm: 4 }}>
            <Card>
              <CardContent sx={{ textAlign: "center" }}>
                <Typography variant="caption" color="text.secondary">
                  Original Score
                </Typography>
                <Typography variant="h4" fontWeight={700} color="error.main">
                  {Math.round(result.originalScore)}%
                </Typography>
                <Chip label="AI Detected" size="small" color="error" />
              </CardContent>
            </Card>
          </Grid>
          <Grid size={{ xs: 12, sm: 4 }}>
            <Card>
              <CardContent sx={{ textAlign: "center" }}>
                <Typography variant="caption" color="text.secondary">
                  Humanized Score
                </Typography>
                <Typography variant="h4" fontWeight={700} color="success.main">
                  {Math.round(result.humanizedScore)}%
                </Typography>
                <Chip label="Passes Detection" size="small" color="success" />
              </CardContent>
            </Card>
          </Grid>
          <Grid size={{ xs: 12, sm: 4 }}>
            <Card>
              <CardContent sx={{ textAlign: "center" }}>
                <Typography variant="caption" color="text.secondary">
                  Score Reduction
                </Typography>
                <Typography
                  variant="h4"
                  fontWeight={700}
                  sx={{ color: scoreDropColor }}
                >
                  -{Math.round(scoreDrop)}
                </Typography>
                <Chip
                  label={`${result.iterations} iterations`}
                  size="small"
                  variant="outlined"
                />
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        {/* Meaning preservation */}
        <Card>
          <CardContent>
            <Box
              sx={{
                display: "flex",
                justifyContent: "space-between",
                mb: 1,
              }}
            >
              <Typography variant="subtitle2">
                Meaning Preservation
              </Typography>
              <Typography variant="subtitle2" fontWeight={700}>
                {Math.round(result.meaningPreservation * 100)}%
              </Typography>
            </Box>
            <LinearProgress
              variant="determinate"
              value={result.meaningPreservation * 100}
              sx={{
                height: 8,
                borderRadius: 4,
                backgroundColor: "divider",
                "& .MuiLinearProgress-bar": {
                  borderRadius: 4,
                  background: "linear-gradient(90deg, #7c3aed, #06b6d4)",
                },
              }}
            />
            <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5 }}>
              How well the humanized version preserves the original meaning
            </Typography>
          </CardContent>
        </Card>

        {/* Score timeline chart */}
        {result.scoreTimeline.length > 1 && (
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Score Timeline
              </Typography>
              <Box sx={{ width: "100%", height: 250 }}>
                <ResponsiveContainer>
                  <LineChart data={result.scoreTimeline}>
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke={theme.palette.divider}
                    />
                    <XAxis
                      dataKey="iteration"
                      tick={{ fill: theme.palette.text.secondary, fontSize: 12 }}
                      label={{
                        value: "Iteration",
                        position: "insideBottom",
                        offset: -5,
                        fill: theme.palette.text.secondary,
                      }}
                    />
                    <YAxis
                      domain={[0, 100]}
                      tick={{ fill: theme.palette.text.secondary, fontSize: 12 }}
                      label={{
                        value: "AI Score %",
                        angle: -90,
                        position: "insideLeft",
                        fill: theme.palette.text.secondary,
                      }}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: theme.palette.background.paper,
                        border: `1px solid ${theme.palette.divider}`,
                        borderRadius: 8,
                        color: theme.palette.text.primary,
                      }}
                    />
                    <Line
                      type="monotone"
                      dataKey="score"
                      stroke={theme.palette.primary.main}
                      strokeWidth={2}
                      dot={{
                        fill: theme.palette.primary.main,
                        strokeWidth: 0,
                        r: 4,
                      }}
                      activeDot={{ r: 6 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </Box>
            </CardContent>
          </Card>
        )}

        {/* Split view: Original vs Humanized */}
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Comparison
            </Typography>
            <Divider sx={{ mb: 2 }} />
            <Grid container spacing={3}>
              <Grid size={{ xs: 12, md: 6 }}>
                <Box>
                  <Chip
                    label="Original"
                    color="error"
                    size="small"
                    sx={{ mb: 1.5 }}
                  />
                  <Typography
                    variant="body2"
                    sx={{
                      p: 2,
                      borderRadius: 2,
                      backgroundColor: "background.default",
                      border: "1px solid",
                      borderColor: "divider",
                      lineHeight: 1.8,
                      whiteSpace: "pre-wrap",
                      maxHeight: 400,
                      overflow: "auto",
                    }}
                  >
                    {result.originalText}
                  </Typography>
                </Box>
              </Grid>
              <Grid size={{ xs: 12, md: 6 }}>
                <Box>
                  <Chip
                    label="Humanized"
                    color="success"
                    size="small"
                    sx={{ mb: 1.5 }}
                  />
                  <Typography
                    variant="body2"
                    sx={{
                      p: 2,
                      borderRadius: 2,
                      backgroundColor: "background.default",
                      border: "1px solid",
                      borderColor: "divider",
                      lineHeight: 1.8,
                      whiteSpace: "pre-wrap",
                      maxHeight: 400,
                      overflow: "auto",
                    }}
                  >
                    {result.humanizedText}
                  </Typography>
                </Box>
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      </Box>
    </motion.div>
  );
}
