import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  useTheme,
} from "@mui/material";
import Grid from "@mui/material/Grid2";
import MenuBookOutlinedIcon from "@mui/icons-material/MenuBookOutlined";
import TimerOutlinedIcon from "@mui/icons-material/TimerOutlined";
import { motion } from "framer-motion";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import type { ReadabilityResult } from "@/types/analytics";

interface ReadabilityPanelProps {
  data: ReadabilityResult;
}

function CircularGauge({
  value,
  maxValue,
  label,
  size = 110,
  delay = 0,
}: {
  value: number;
  maxValue: number;
  label: string;
  size?: number;
  delay?: number;
}) {
  const theme = useTheme();
  const normalizedValue = Math.min(Math.max(value / maxValue, 0), 1);
  const strokeWidth = 8;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference * (1 - normalizedValue);

  const getColor = () => {
    if (normalizedValue > 0.7) return theme.palette.success.main;
    if (normalizedValue > 0.4) return theme.palette.warning.main;
    return theme.palette.error.main;
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ delay, duration: 0.5, ease: "easeOut" }}
    >
      <Box sx={{ textAlign: "center" }}>
        <Box sx={{ position: "relative", display: "inline-block" }}>
          <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
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
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Typography variant="h6" fontWeight={700} sx={{ fontSize: "1rem" }}>
              {typeof value === "number" ? value.toFixed(1) : value}
            </Typography>
          </Box>
        </Box>
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{ display: "block", mt: 0.5, fontSize: "0.7rem" }}
        >
          {label}
        </Typography>
      </Box>
    </motion.div>
  );
}

const difficultyColors: Record<string, string> = {
  very_easy: "#22c55e",
  easy: "#4ade80",
  moderate: "#f59e0b",
  difficult: "#f87171",
  very_difficult: "#ef4444",
};

export default function ReadabilityPanel({ data }: ReadabilityPanelProps) {
  const theme = useTheme();

  const chartData = [
    { name: "Flesch RE", value: data.flesch_reading_ease, max: 100 },
    { name: "F-K Grade", value: data.flesch_kincaid_grade, max: 20 },
    { name: "Gunning Fog", value: data.gunning_fog, max: 20 },
    { name: "SMOG", value: data.smog_index, max: 20 },
    { name: "Coleman-Liau", value: data.coleman_liau, max: 20 },
    { name: "ARI", value: data.automated_readability, max: 20 },
    { name: "Dale-Chall", value: data.dale_chall, max: 12 },
    { name: "Linsear Write", value: data.linsear_write, max: 20 },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
        {/* Top row: Grade + Reading Time */}
        <Grid container spacing={2}>
          <Grid size={{ xs: 12, sm: 6, md: 4 }}>
            <Card>
              <CardContent sx={{ textAlign: "center", py: 3 }}>
                <Typography variant="overline" color="text.secondary">
                  Overall Grade
                </Typography>
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ delay: 0.2, type: "spring", stiffness: 200 }}
                >
                  <Chip
                    label={data.overall_grade}
                    sx={{
                      mt: 1,
                      fontSize: "1.5rem",
                      fontWeight: 800,
                      height: 56,
                      px: 3,
                      backgroundColor:
                        difficultyColors[data.difficulty] || theme.palette.primary.main,
                      color: "#fff",
                    }}
                  />
                </motion.div>
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{ mt: 1, textTransform: "capitalize" }}
                >
                  {data.difficulty.replace("_", " ")}
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid size={{ xs: 12, sm: 6, md: 4 }}>
            <Card>
              <CardContent sx={{ textAlign: "center", py: 3 }}>
                <Typography variant="overline" color="text.secondary">
                  Reading Time
                </Typography>
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: 1,
                    mt: 1,
                  }}
                >
                  <MenuBookOutlinedIcon
                    sx={{ fontSize: 32, color: "primary.main" }}
                  />
                  <Typography variant="h4" fontWeight={700}>
                    {data.reading_time_minutes.toFixed(1)}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    min
                  </Typography>
                </Box>
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: 0.5,
                    mt: 0.5,
                  }}
                >
                  <TimerOutlinedIcon
                    sx={{ fontSize: 16, color: "text.secondary" }}
                  />
                  <Typography variant="caption" color="text.secondary">
                    {data.reading_time_seconds}s at avg speed
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid size={{ xs: 12, md: 4 }}>
            <Card>
              <CardContent sx={{ textAlign: "center", py: 3 }}>
                <Typography variant="overline" color="text.secondary">
                  Flesch Reading Ease
                </Typography>
                <CircularGauge
                  value={data.flesch_reading_ease}
                  maxValue={100}
                  label="out of 100"
                  size={100}
                />
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        {/* Gauges row */}
        <Card>
          <CardContent>
            <Typography variant="subtitle2" fontWeight={600} gutterBottom>
              Readability Indices
            </Typography>
            <Box
              sx={{
                display: "flex",
                flexWrap: "wrap",
                justifyContent: "center",
                gap: 3,
                mt: 2,
              }}
            >
              <CircularGauge
                value={data.flesch_kincaid_grade}
                maxValue={20}
                label="Flesch-Kincaid"
                delay={0}
              />
              <CircularGauge
                value={data.gunning_fog}
                maxValue={20}
                label="Gunning Fog"
                delay={0.1}
              />
              <CircularGauge
                value={data.smog_index}
                maxValue={20}
                label="SMOG"
                delay={0.2}
              />
              <CircularGauge
                value={data.coleman_liau}
                maxValue={20}
                label="Coleman-Liau"
                delay={0.3}
              />
              <CircularGauge
                value={data.automated_readability}
                maxValue={20}
                label="ARI"
                delay={0.4}
              />
              <CircularGauge
                value={data.dale_chall}
                maxValue={12}
                label="Dale-Chall"
                delay={0.5}
              />
              <CircularGauge
                value={data.linsear_write}
                maxValue={20}
                label="Linsear Write"
                delay={0.6}
              />
            </Box>
          </CardContent>
        </Card>

        {/* Bar Chart comparison */}
        <Card>
          <CardContent>
            <Typography variant="subtitle2" fontWeight={600} gutterBottom>
              Index Comparison
            </Typography>
            <Box sx={{ width: "100%", height: 320, mt: 2 }}>
              <ResponsiveContainer>
                <BarChart data={chartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke={theme.palette.divider}
                  />
                  <XAxis
                    dataKey="name"
                    tick={{ fontSize: 11, fill: theme.palette.text.secondary }}
                  />
                  <YAxis
                    tick={{ fontSize: 11, fill: theme.palette.text.secondary }}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: theme.palette.background.paper,
                      border: `1px solid ${theme.palette.divider}`,
                      borderRadius: 8,
                    }}
                  />
                  <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                    {chartData.map((entry, index) => {
                      const norm = entry.value / entry.max;
                      let color = theme.palette.success.main;
                      if (norm > 0.7) color = theme.palette.error.main;
                      else if (norm > 0.4) color = theme.palette.warning.main;
                      if (entry.name === "Flesch RE") {
                        color =
                          norm > 0.6
                            ? theme.palette.success.main
                            : norm > 0.3
                            ? theme.palette.warning.main
                            : theme.palette.error.main;
                      }
                      return <Cell key={index} fill={color} />;
                    })}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </Box>
          </CardContent>
        </Card>
      </Box>
    </motion.div>
  );
}
