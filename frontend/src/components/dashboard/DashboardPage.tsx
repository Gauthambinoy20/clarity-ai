import { useState, useEffect, useCallback } from "react";
import {
  Box,
  Typography,
  Card,
  CardContent,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  CircularProgress,
  Alert,
  useTheme,
} from "@mui/material";
import Grid from "@mui/material/Grid2";
import BarChartIcon from "@mui/icons-material/BarChart";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import TextFieldsIcon from "@mui/icons-material/TextFields";
import TodayIcon from "@mui/icons-material/Today";
import { motion, useMotionValue, useTransform, animate } from "framer-motion";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import {
  getDashboardStats,
  getDashboardTrends,
  getTopSignals,
} from "@/utils/api";
import type { DashboardStats, DashboardTrends, TopSignal } from "@/types/analytics";

function AnimatedCount({ value, duration = 1.5 }: { value: number; duration?: number }) {
  const motionVal = useMotionValue(0);
  const rounded = useTransform(motionVal, (v) =>
    v >= 1000 ? `${(v / 1000).toFixed(1)}k` : Math.round(v).toLocaleString()
  );
  const [display, setDisplay] = useState("0");

  useEffect(() => {
    const controls = animate(motionVal, value, {
      duration,
      ease: "easeOut",
    });
    const unsub = rounded.on("change", (v) => setDisplay(v));
    return () => {
      controls.stop();
      unsub();
    };
  }, [value, duration, motionVal, rounded]);

  return <>{display}</>;
}

const PIE_COLORS = ["#ef4444", "#22c55e", "#f59e0b"];

const statCards = [
  { key: "totalAnalyses", label: "Total Analyses", icon: BarChartIcon, color: "#7c3aed" },
  { key: "avgAiScore", label: "Avg AI Score", icon: TrendingUpIcon, color: "#06b6d4" },
  { key: "totalWords", label: "Total Words", icon: TextFieldsIcon, color: "#ec4899" },
  { key: "analysesToday", label: "Analyses Today", icon: TodayIcon, color: "#f59e0b" },
] as const;

export default function DashboardPage() {
  const theme = useTheme();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [trends, setTrends] = useState<DashboardTrends | null>(null);
  const [signals, setSignals] = useState<TopSignal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [s, t, sig] = await Promise.all([
        getDashboardStats(),
        getDashboardTrends(),
        getTopSignals(10),
      ]);
      setStats(s);
      setTrends(t);
      setSignals(sig);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load dashboard data";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  if (loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: 400 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ maxWidth: 1200, mx: "auto" }}>
        <Alert severity="error" sx={{ borderRadius: 2 }}>
          {error}
        </Alert>
      </Box>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
    >
      <Box sx={{ maxWidth: 1400, mx: "auto" }}>
        {/* Header */}
        <Box sx={{ mb: 4 }}>
          <Typography variant="h4" fontWeight={700} gutterBottom>
            Dashboard
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Overview of your content analysis activity and trends.
          </Typography>
        </Box>

        {/* Stat Cards */}
        <Grid container spacing={3} sx={{ mb: 4 }}>
          {statCards.map((card, i) => {
            const Icon = card.icon;
            const value = stats ? stats[card.key] : 0;
            return (
              <Grid size={{ xs: 12, sm: 6, md: 3 }} key={card.key}>
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.1, duration: 0.4 }}
                >
                  <Paper
                    elevation={0}
                    sx={{
                      p: 3,
                      borderRadius: 3,
                      border: `1px solid ${theme.palette.divider}`,
                      display: "flex",
                      alignItems: "center",
                      gap: 2,
                    }}
                  >
                    <Box
                      sx={{
                        width: 48,
                        height: 48,
                        borderRadius: 2,
                        backgroundColor: `${card.color}15`,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                      }}
                    >
                      <Icon sx={{ color: card.color, fontSize: 26 }} />
                    </Box>
                    <Box>
                      <Typography variant="caption" color="text.secondary">
                        {card.label}
                      </Typography>
                      <Typography variant="h5" fontWeight={700}>
                        <AnimatedCount value={value} />
                      </Typography>
                    </Box>
                  </Paper>
                </motion.div>
              </Grid>
            );
          })}
        </Grid>

        {/* Charts Row 1: Score Distribution + Analyses Per Day */}
        <Grid container spacing={3} sx={{ mb: 4 }}>
          <Grid size={{ xs: 12, md: 6 }}>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
            >
              <Paper
                elevation={0}
                sx={{ p: 3, borderRadius: 3, border: `1px solid ${theme.palette.divider}` }}
              >
                <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                  AI Score Distribution
                </Typography>
                {trends && trends.scoreDistribution.length > 0 ? (
                  <ResponsiveContainer width="100%" height={260}>
                    <BarChart data={trends.scoreDistribution}>
                      <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} />
                      <XAxis
                        dataKey="range"
                        tick={{ fontSize: 11, fill: theme.palette.text.secondary }}
                      />
                      <YAxis tick={{ fontSize: 11, fill: theme.palette.text.secondary }} />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: theme.palette.background.paper,
                          border: `1px solid ${theme.palette.divider}`,
                          borderRadius: 8,
                          fontSize: 13,
                        }}
                      />
                      <Bar
                        dataKey="count"
                        fill="#7c3aed"
                        radius={[4, 4, 0, 0]}
                        name="Analyses"
                      />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <Box sx={{ height: 260, display: "flex", alignItems: "center", justifyContent: "center" }}>
                    <Typography color="text.secondary">No data available</Typography>
                  </Box>
                )}
              </Paper>
            </motion.div>
          </Grid>

          <Grid size={{ xs: 12, md: 6 }}>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 }}
            >
              <Paper
                elevation={0}
                sx={{ p: 3, borderRadius: 3, border: `1px solid ${theme.palette.divider}` }}
              >
                <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                  Analyses Per Day (Last 30 Days)
                </Typography>
                {trends && trends.analysesPerDay.length > 0 ? (
                  <ResponsiveContainer width="100%" height={260}>
                    <LineChart data={trends.analysesPerDay}>
                      <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} />
                      <XAxis
                        dataKey="date"
                        tick={{ fontSize: 10, fill: theme.palette.text.secondary }}
                        tickFormatter={(val: string) => val.slice(5)}
                      />
                      <YAxis tick={{ fontSize: 11, fill: theme.palette.text.secondary }} />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: theme.palette.background.paper,
                          border: `1px solid ${theme.palette.divider}`,
                          borderRadius: 8,
                          fontSize: 13,
                        }}
                      />
                      <Line
                        type="monotone"
                        dataKey="count"
                        stroke="#06b6d4"
                        strokeWidth={2}
                        dot={{ fill: "#06b6d4", r: 3 }}
                        activeDot={{ r: 5 }}
                        name="Analyses"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <Box sx={{ height: 260, display: "flex", alignItems: "center", justifyContent: "center" }}>
                    <Typography color="text.secondary">No data available</Typography>
                  </Box>
                )}
              </Paper>
            </motion.div>
          </Grid>
        </Grid>

        {/* Charts Row 2: Top Signals + Classification Pie */}
        <Grid container spacing={3} sx={{ mb: 4 }}>
          <Grid size={{ xs: 12, md: 7 }}>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 }}
            >
              <Paper
                elevation={0}
                sx={{ p: 3, borderRadius: 3, border: `1px solid ${theme.palette.divider}` }}
              >
                <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                  Top Firing Signals
                </Typography>
                {signals.length > 0 ? (
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={signals} layout="vertical" margin={{ left: 80 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} />
                      <XAxis
                        type="number"
                        tick={{ fontSize: 11, fill: theme.palette.text.secondary }}
                      />
                      <YAxis
                        dataKey="name"
                        type="category"
                        tick={{ fontSize: 11, fill: theme.palette.text.secondary }}
                        width={80}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: theme.palette.background.paper,
                          border: `1px solid ${theme.palette.divider}`,
                          borderRadius: 8,
                          fontSize: 13,
                        }}
                      />
                      <Bar dataKey="count" fill="#ec4899" radius={[0, 4, 4, 0]} name="Count" />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <Box sx={{ height: 300, display: "flex", alignItems: "center", justifyContent: "center" }}>
                    <Typography color="text.secondary">No signal data</Typography>
                  </Box>
                )}
              </Paper>
            </motion.div>
          </Grid>

          <Grid size={{ xs: 12, md: 5 }}>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6 }}
            >
              <Paper
                elevation={0}
                sx={{ p: 3, borderRadius: 3, border: `1px solid ${theme.palette.divider}` }}
              >
                <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                  Classification Breakdown
                </Typography>
                {trends && trends.classificationBreakdown.length > 0 ? (
                  <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
                    <ResponsiveContainer width="100%" height={220}>
                      <PieChart>
                        <Pie
                          data={trends.classificationBreakdown}
                          cx="50%"
                          cy="50%"
                          innerRadius={55}
                          outerRadius={85}
                          dataKey="value"
                          nameKey="label"
                          paddingAngle={3}
                          strokeWidth={0}
                        >
                          {trends.classificationBreakdown.map((_entry, index) => (
                            <Cell
                              key={`cell-${index}`}
                              fill={PIE_COLORS[index % PIE_COLORS.length]}
                            />
                          ))}
                        </Pie>
                        <Tooltip
                          contentStyle={{
                            backgroundColor: theme.palette.background.paper,
                            border: `1px solid ${theme.palette.divider}`,
                            borderRadius: 8,
                            fontSize: 13,
                          }}
                        />
                      </PieChart>
                    </ResponsiveContainer>
                    <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap", justifyContent: "center" }}>
                      {trends.classificationBreakdown.map((item, i) => (
                        <Box key={item.label} sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                          <Box
                            sx={{
                              width: 12,
                              height: 12,
                              borderRadius: "50%",
                              backgroundColor: PIE_COLORS[i % PIE_COLORS.length],
                            }}
                          />
                          <Typography variant="caption">
                            {item.label} ({item.value})
                          </Typography>
                        </Box>
                      ))}
                    </Box>
                  </Box>
                ) : (
                  <Box sx={{ height: 260, display: "flex", alignItems: "center", justifyContent: "center" }}>
                    <Typography color="text.secondary">No data available</Typography>
                  </Box>
                )}
              </Paper>
            </motion.div>
          </Grid>
        </Grid>

        {/* Recent Analyses Table */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7 }}
        >
          <Paper
            elevation={0}
            sx={{ borderRadius: 3, border: `1px solid ${theme.palette.divider}`, overflow: "hidden" }}
          >
            <Box sx={{ p: 3, pb: 0 }}>
              <Typography variant="subtitle1" fontWeight={600}>
                Recent Analyses
              </Typography>
            </Box>
            {trends && trends.recentAnalyses.length > 0 ? (
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell sx={{ fontWeight: 600 }}>Text Preview</TableCell>
                      <TableCell align="center" sx={{ fontWeight: 600 }}>
                        Score
                      </TableCell>
                      <TableCell align="center" sx={{ fontWeight: 600 }}>
                        Label
                      </TableCell>
                      <TableCell align="right" sx={{ fontWeight: 600 }}>
                        Date
                      </TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {trends.recentAnalyses.map((item) => {
                      const labelColor =
                        item.label === "ai"
                          ? "#ef4444"
                          : item.label === "human"
                          ? "#22c55e"
                          : "#f59e0b";
                      return (
                        <TableRow key={item.id} hover>
                          <TableCell>
                            <Typography
                              variant="body2"
                              sx={{
                                maxWidth: 400,
                                overflow: "hidden",
                                textOverflow: "ellipsis",
                                whiteSpace: "nowrap",
                              }}
                            >
                              {item.textPreview}
                            </Typography>
                          </TableCell>
                          <TableCell align="center">
                            <Typography variant="body2" fontWeight={600}>
                              {item.score}%
                            </Typography>
                          </TableCell>
                          <TableCell align="center">
                            <Chip
                              label={item.label}
                              size="small"
                              sx={{
                                backgroundColor: `${labelColor}20`,
                                color: labelColor,
                                fontWeight: 600,
                                textTransform: "capitalize",
                              }}
                            />
                          </TableCell>
                          <TableCell align="right">
                            <Typography variant="caption" color="text.secondary">
                              {new Date(item.createdAt).toLocaleDateString()}
                            </Typography>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </TableContainer>
            ) : (
              <Box sx={{ p: 4, textAlign: "center" }}>
                <Typography color="text.secondary">No recent analyses</Typography>
              </Box>
            )}
          </Paper>
        </motion.div>
      </Box>
    </motion.div>
  );
}
