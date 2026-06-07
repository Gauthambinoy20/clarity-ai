import { useState, useCallback } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  List,
  ListItem,
  Alert,
  Chip,
  IconButton,
  Tooltip,
  Collapse,
  useTheme,
} from "@mui/material";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutline";
import WarningAmberOutlinedIcon from "@mui/icons-material/WarningAmberOutlined";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import { motion, AnimatePresence } from "framer-motion";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  Legend,
} from "recharts";
import type { GrammarResult, GrammarError } from "@/types/analytics";

interface GrammarCheckerProps {
  data: GrammarResult;
  onAcceptSuggestion?: (error: GrammarError, suggestion: string) => void;
}

const severityConfig = {
  error: {
    icon: <ErrorOutlineIcon />,
    color: "#ef4444",
    bgColor: "rgba(239,68,68,0.1)",
    label: "Error",
  },
  warning: {
    icon: <WarningAmberOutlinedIcon />,
    color: "#f59e0b",
    bgColor: "rgba(245,158,11,0.1)",
    label: "Warning",
  },
  info: {
    icon: <InfoOutlinedIcon />,
    color: "#3b82f6",
    bgColor: "rgba(59,130,246,0.1)",
    label: "Info",
  },
};

const PIE_COLORS = [
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
];

function ScoreGauge({
  score,
  label,
  delay = 0,
}: {
  score: number;
  label: string;
  delay?: number;
}) {
  const theme = useTheme();
  const size = 120;
  const strokeWidth = 10;
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
              transition={{ delay: delay + 0.3, duration: 1, ease: "easeOut" }}
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
            <Typography variant="h5" fontWeight={700}>
              {score}
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: "0.65rem" }}>
              / 100
            </Typography>
          </Box>
        </Box>
        <Typography variant="body2" fontWeight={600} sx={{ mt: 0.5 }}>
          {label}
        </Typography>
      </Box>
    </motion.div>
  );
}

export default function GrammarChecker({
  data,
  onAcceptSuggestion,
}: GrammarCheckerProps) {
  const theme = useTheme();
  const [dismissedIds, setDismissedIds] = useState<Set<string>>(new Set());

  const handleAccept = useCallback(
    (error: GrammarError, suggestion: string) => {
      setDismissedIds((prev) => new Set(prev).add(error.id));
      onAcceptSuggestion?.(error, suggestion);
    },
    [onAcceptSuggestion]
  );

  const categoryData = Object.entries(data.category_counts).map(
    ([name, value]) => ({ name, value })
  );

  const visibleErrors = data.errors.filter((e) => !dismissedIds.has(e.id));

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
        {/* Score gauges */}
        <Box
          sx={{
            display: "flex",
            justifyContent: "center",
            gap: 6,
            flexWrap: "wrap",
          }}
        >
          <ScoreGauge score={data.grammar_score} label="Grammar Score" delay={0} />
          <ScoreGauge score={data.style_score} label="Style Score" delay={0.2} />
        </Box>

        {/* Summary */}
        <Card>
          <CardContent>
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 2,
                flexWrap: "wrap",
              }}
            >
              <Alert
                severity={data.total_errors === 0 ? "success" : "info"}
                sx={{ flex: 1, borderRadius: 2 }}
              >
                {data.total_errors === 0
                  ? "No issues found. Your text looks great!"
                  : `Found ${data.total_errors} issue${data.total_errors !== 1 ? "s" : ""} in your text.`}
              </Alert>
              <Chip
                label={`${visibleErrors.length} remaining`}
                size="small"
                color="primary"
                variant="outlined"
              />
            </Box>
          </CardContent>
        </Card>

        {/* Category Breakdown + Error List */}
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" },
            gap: 3,
          }}
        >
          {/* Pie Chart */}
          <Card>
            <CardContent>
              <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                Issue Categories
              </Typography>
              {categoryData.length > 0 ? (
                <Box sx={{ width: "100%", height: 280 }}>
                  <ResponsiveContainer>
                    <PieChart>
                      <Pie
                        data={categoryData}
                        cx="50%"
                        cy="50%"
                        innerRadius={55}
                        outerRadius={90}
                        paddingAngle={3}
                        dataKey="value"
                      >
                        {categoryData.map((_, index) => (
                          <Cell
                            key={index}
                            fill={PIE_COLORS[index % PIE_COLORS.length]}
                          />
                        ))}
                      </Pie>
                      <RechartsTooltip
                        contentStyle={{
                          backgroundColor: theme.palette.background.paper,
                          border: `1px solid ${theme.palette.divider}`,
                          borderRadius: 8,
                        }}
                      />
                      <Legend
                        wrapperStyle={{ fontSize: 12 }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </Box>
              ) : (
                <Box
                  sx={{
                    height: 280,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <Typography color="text.secondary">No issues to categorize</Typography>
                </Box>
              )}
            </CardContent>
          </Card>

          {/* Error List */}
          <Card>
            <CardContent>
              <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                Issues
              </Typography>
              <List
                sx={{
                  maxHeight: 400,
                  overflow: "auto",
                  "& .MuiListItem-root": { px: 0 },
                }}
              >
                <AnimatePresence>
                  {visibleErrors.map((error, i) => {
                    const config = severityConfig[error.severity];
                    return (
                      <motion.div
                        key={error.id}
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        exit={{ opacity: 0, height: 0 }}
                        transition={{ duration: 0.3 }}
                      >
                        <ListItem
                          sx={{
                            flexDirection: "column",
                            alignItems: "stretch",
                            mb: 1,
                            p: 1.5,
                            borderRadius: 2,
                            backgroundColor: config.bgColor,
                            border: `1px solid ${config.color}33`,
                          }}
                        >
                          <Box
                            sx={{
                              display: "flex",
                              alignItems: "center",
                              gap: 1,
                              mb: 0.5,
                            }}
                          >
                            <Box sx={{ color: config.color }}>{config.icon}</Box>
                            <Typography
                              variant="body2"
                              fontWeight={600}
                              sx={{ flex: 1 }}
                            >
                              {error.message}
                            </Typography>
                            <Chip
                              label={config.label}
                              size="small"
                              sx={{
                                backgroundColor: config.color,
                                color: "#fff",
                                fontWeight: 600,
                                fontSize: "0.65rem",
                                height: 22,
                              }}
                            />
                          </Box>

                          <Box sx={{ ml: 4 }}>
                            <Typography
                              variant="body2"
                              sx={{
                                backgroundColor: "action.hover",
                                borderRadius: 1,
                                px: 1,
                                py: 0.5,
                                fontFamily: "monospace",
                                display: "inline-block",
                                textDecoration: "line-through",
                                color: "error.main",
                              }}
                            >
                              {error.original}
                            </Typography>
                            {error.suggestions.length > 0 && (
                              <Box
                                sx={{
                                  display: "flex",
                                  alignItems: "center",
                                  gap: 1,
                                  mt: 0.5,
                                  flexWrap: "wrap",
                                }}
                              >
                                {error.suggestions.map((s, j) => (
                                  <Tooltip key={j} title="Accept suggestion">
                                    <Chip
                                      label={s}
                                      size="small"
                                      variant="outlined"
                                      clickable
                                      icon={<CheckCircleOutlineIcon />}
                                      onClick={() => handleAccept(error, s)}
                                      sx={{
                                        borderColor: "success.main",
                                        color: "success.main",
                                        fontWeight: 500,
                                        "&:hover": {
                                          backgroundColor: "success.main",
                                          color: "#fff",
                                        },
                                      }}
                                    />
                                  </Tooltip>
                                ))}
                              </Box>
                            )}
                          </Box>
                        </ListItem>
                      </motion.div>
                    );
                  })}
                </AnimatePresence>
                {visibleErrors.length === 0 && (
                  <Box
                    sx={{
                      py: 4,
                      textAlign: "center",
                    }}
                  >
                    <CheckCircleOutlineIcon
                      sx={{ fontSize: 40, color: "success.main", mb: 1 }}
                    />
                    <Typography color="text.secondary">
                      All issues resolved!
                    </Typography>
                  </Box>
                )}
              </List>
            </CardContent>
          </Card>
        </Box>
      </Box>
    </motion.div>
  );
}
