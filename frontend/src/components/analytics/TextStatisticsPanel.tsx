import {
  Box,
  Card,
  CardContent,
  Typography,
  useTheme,
} from "@mui/material";
import Grid from "@mui/material/Grid2";
import TextFieldsOutlinedIcon from "@mui/icons-material/TextFieldsOutlined";
import ShortTextOutlinedIcon from "@mui/icons-material/ShortTextOutlined";
import SubjectOutlinedIcon from "@mui/icons-material/SubjectOutlined";
import AbcOutlinedIcon from "@mui/icons-material/AbcOutlined";
import TimerOutlinedIcon from "@mui/icons-material/TimerOutlined";
import { motion } from "framer-motion";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";
import WordCloud from "@/components/common/WordCloud";
import type { TextStatistics } from "@/types/analytics";

interface TextStatisticsPanelProps {
  data: TextStatistics;
}

const POS_COLORS = [
  "#7c3aed",
  "#06b6d4",
  "#22c55e",
  "#f59e0b",
  "#ef4444",
  "#ec4899",
  "#8b5cf6",
  "#14b8a6",
  "#f97316",
  "#6366f1",
  "#a78bfa",
  "#34d399",
];

interface MetricCardProps {
  icon: React.ReactNode;
  label: string;
  value: string | number;
  subtitle?: string;
  delay?: number;
}

function MetricCard({ icon, label, value, subtitle, delay = 0 }: MetricCardProps) {
  return (
    <Grid size={{ xs: 6, sm: 4, md: 2.4 }}>
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay, duration: 0.4 }}
      >
        <Card sx={{ height: "100%" }}>
          <CardContent sx={{ textAlign: "center", py: 2.5, px: 1.5 }}>
            <Box sx={{ color: "primary.main", mb: 0.5 }}>{icon}</Box>
            <Typography variant="h5" fontWeight={700}>
              {typeof value === "number" ? value.toLocaleString() : value}
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>
              {label}
            </Typography>
            {subtitle && (
              <Typography
                variant="caption"
                color="text.secondary"
                sx={{ fontSize: "0.65rem" }}
              >
                {subtitle}
              </Typography>
            )}
          </CardContent>
        </Card>
      </motion.div>
    </Grid>
  );
}

export default function TextStatisticsPanel({ data }: TextStatisticsPanelProps) {
  const theme = useTheme();

  const topWords = data.common_words.slice(0, 20);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
        {/* Key metrics */}
        <Grid container spacing={2}>
          <MetricCard
            icon={<TextFieldsOutlinedIcon />}
            label="Words"
            value={data.word_count}
            delay={0}
          />
          <MetricCard
            icon={<ShortTextOutlinedIcon />}
            label="Sentences"
            value={data.sentence_count}
            delay={0.05}
          />
          <MetricCard
            icon={<SubjectOutlinedIcon />}
            label="Paragraphs"
            value={data.paragraph_count}
            delay={0.1}
          />
          <MetricCard
            icon={<AbcOutlinedIcon />}
            label="Unique Words"
            value={data.unique_word_count}
            subtitle={`${(data.vocabulary_richness * 100).toFixed(1)}% richness`}
            delay={0.15}
          />
          <MetricCard
            icon={<TimerOutlinedIcon />}
            label="Reading Time"
            value={`${data.reading_time_minutes.toFixed(1)}m`}
            subtitle={`${data.speaking_time_minutes.toFixed(1)}m speaking`}
            delay={0.2}
          />
        </Grid>

        {/* Charts row */}
        <Grid container spacing={3}>
          {/* Word length distribution */}
          <Grid size={{ xs: 12, md: 6 }}>
            <Card>
              <CardContent>
                <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                  Word Length Distribution
                </Typography>
                <Box sx={{ width: "100%", height: 260, mt: 1 }}>
                  <ResponsiveContainer>
                    <BarChart data={data.word_length_distribution}>
                      <CartesianGrid
                        strokeDasharray="3 3"
                        stroke={theme.palette.divider}
                      />
                      <XAxis
                        dataKey="length"
                        tick={{ fontSize: 11, fill: theme.palette.text.secondary }}
                        label={{
                          value: "Letters",
                          position: "insideBottom",
                          offset: -5,
                          fontSize: 11,
                          fill: theme.palette.text.secondary,
                        }}
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
                      <Bar
                        dataKey="count"
                        fill={theme.palette.primary.main}
                        radius={[3, 3, 0, 0]}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          {/* Sentence length distribution */}
          <Grid size={{ xs: 12, md: 6 }}>
            <Card>
              <CardContent>
                <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                  Sentence Length Distribution
                </Typography>
                <Box sx={{ width: "100%", height: 260, mt: 1 }}>
                  <ResponsiveContainer>
                    <BarChart data={data.sentence_length_distribution}>
                      <CartesianGrid
                        strokeDasharray="3 3"
                        stroke={theme.palette.divider}
                      />
                      <XAxis
                        dataKey="length"
                        tick={{ fontSize: 11, fill: theme.palette.text.secondary }}
                        label={{
                          value: "Words",
                          position: "insideBottom",
                          offset: -5,
                          fontSize: 11,
                          fill: theme.palette.text.secondary,
                        }}
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
                      <Bar
                        dataKey="count"
                        fill={theme.palette.secondary.main}
                        radius={[3, 3, 0, 0]}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        <Grid container spacing={3}>
          {/* POS distribution donut */}
          <Grid size={{ xs: 12, md: 5 }}>
            <Card>
              <CardContent>
                <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                  Part-of-Speech Distribution
                </Typography>
                <Box sx={{ width: "100%", height: 300 }}>
                  <ResponsiveContainer>
                    <PieChart>
                      <Pie
                        data={data.pos_distribution}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={100}
                        paddingAngle={2}
                        dataKey="count"
                        nameKey="label"
                      >
                        {data.pos_distribution.map((_, index) => (
                          <Cell
                            key={index}
                            fill={POS_COLORS[index % POS_COLORS.length]}
                          />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{
                          backgroundColor: theme.palette.background.paper,
                          border: `1px solid ${theme.palette.divider}`,
                          borderRadius: 8,
                        }}
                      />
                      <Legend wrapperStyle={{ fontSize: 11 }} />
                    </PieChart>
                  </ResponsiveContainer>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          {/* Top 20 common words */}
          <Grid size={{ xs: 12, md: 7 }}>
            <Card>
              <CardContent>
                <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                  Top 20 Common Words
                </Typography>
                <Box sx={{ width: "100%", height: 300, mt: 1 }}>
                  <ResponsiveContainer>
                    <BarChart
                      data={topWords}
                      layout="vertical"
                      margin={{ top: 5, right: 20, left: 60, bottom: 5 }}
                    >
                      <CartesianGrid
                        strokeDasharray="3 3"
                        stroke={theme.palette.divider}
                      />
                      <XAxis
                        type="number"
                        tick={{ fontSize: 11, fill: theme.palette.text.secondary }}
                      />
                      <YAxis
                        type="category"
                        dataKey="word"
                        tick={{ fontSize: 11, fill: theme.palette.text.secondary }}
                        width={55}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: theme.palette.background.paper,
                          border: `1px solid ${theme.palette.divider}`,
                          borderRadius: 8,
                        }}
                      />
                      <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                        {topWords.map((_, index) => (
                          <Cell
                            key={index}
                            fill={POS_COLORS[index % POS_COLORS.length]}
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        {/* Word Cloud */}
        <Card>
          <CardContent>
            <Typography variant="subtitle2" fontWeight={600} gutterBottom>
              Word Cloud
            </Typography>
            <WordCloud words={data.word_cloud_data} height={350} />
          </CardContent>
        </Card>
      </Box>
    </motion.div>
  );
}
