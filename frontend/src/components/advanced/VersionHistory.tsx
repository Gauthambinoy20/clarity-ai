import { useState } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  alpha,
  useTheme,
  IconButton,
  Tooltip,
  Paper,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import HistoryIcon from "@mui/icons-material/History";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import TrendingDownIcon from "@mui/icons-material/TrendingDown";
import FiberManualRecordIcon from "@mui/icons-material/FiberManualRecord";
import { motion, AnimatePresence } from "framer-motion";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  Area,
  AreaChart,
} from "recharts";

/* ─── Types ──────────────────────────────────────────────────────── */

export interface DiffSegment {
  type: "added" | "removed" | "unchanged";
  text: string;
}

export interface VersionEntry {
  id: string;
  versionNumber: number;
  timestamp: string;
  aiScore: number;
  wordCount: number;
  diff?: DiffSegment[];
}

interface VersionHistoryProps {
  versions: VersionEntry[];
  onVersionSelect?: (version: VersionEntry) => void;
}

/* ─── Helpers ────────────────────────────────────────────────────── */

const scoreColor = (score: number) => {
  if (score > 70) return "#ef4444";
  if (score > 40) return "#f59e0b";
  return "#22c55e";
};

const formatDate = (ts: string) => {
  const d = new Date(ts);
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
};

/* ─── Score Change Badge ─────────────────────────────────────────── */

function ScoreChangeBadge({ current, previous }: { current: number; previous: number }) {
  const diff = current - previous;
  if (diff === 0) return null;
  const isUp = diff > 0;
  const color = isUp ? "#ef4444" : "#22c55e";
  const Icon = isUp ? TrendingUpIcon : TrendingDownIcon;

  return (
    <Chip
      icon={<Icon sx={{ fontSize: 14 }} />}
      label={`${isUp ? "+" : ""}${diff}%`}
      size="small"
      sx={{
        backgroundColor: alpha(color, 0.12),
        color,
        fontWeight: 700,
        fontSize: "0.7rem",
        "& .MuiChip-icon": { color },
      }}
    />
  );
}

/* ─── Diff Display ───────────────────────────────────────────────── */

function DiffView({ segments }: { segments: DiffSegment[] }) {
  const theme = useTheme();

  return (
    <Box
      sx={{
        p: 2,
        borderRadius: 2,
        backgroundColor: alpha(theme.palette.background.default, 0.6),
        fontFamily: "monospace",
        fontSize: "0.82rem",
        lineHeight: 1.8,
        maxHeight: 200,
        overflow: "auto",
      }}
    >
      {segments.map((seg, i) => {
        let style: React.CSSProperties = {};
        if (seg.type === "added") {
          style = {
            backgroundColor: alpha("#22c55e", 0.15),
            color: "#22c55e",
            textDecoration: "none",
          };
        } else if (seg.type === "removed") {
          style = {
            backgroundColor: alpha("#ef4444", 0.15),
            color: "#ef4444",
            textDecoration: "line-through",
          };
        }
        return (
          <span key={i} style={style}>
            {seg.text}
          </span>
        );
      })}
    </Box>
  );
}

/* ─── Main Component ─────────────────────────────────────────────── */

export default function VersionHistory({ versions, onVersionSelect }: VersionHistoryProps) {
  const theme = useTheme();
  const [expandedId, setExpandedId] = useState<string | null>(null);

  if (versions.length === 0) {
    return (
      <Card>
        <CardContent sx={{ p: 3, textAlign: "center" }}>
          <HistoryIcon sx={{ fontSize: 48, color: "text.disabled", mb: 1 }} />
          <Typography variant="body2" color="text.secondary">
            No version history available yet.
          </Typography>
        </CardContent>
      </Card>
    );
  }

  const chartData = versions.map((v) => ({
    version: `v${v.versionNumber}`,
    score: v.aiScore,
  }));

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
      {/* Score Trend Chart */}
      <Card>
        <CardContent sx={{ p: 2.5, "&:last-child": { pb: 2.5 } }}>
          <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 2 }}>
            AI Score Trend Across Versions
          </Typography>
          <Box sx={{ height: 200 }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="vhScoreGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={theme.palette.primary.main} stopOpacity={0.3} />
                    <stop offset="95%" stopColor={theme.palette.primary.main} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke={alpha(theme.palette.divider, 0.2)} />
                <XAxis
                  dataKey="version"
                  tick={{ fill: theme.palette.text.secondary, fontSize: 12 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  domain={[0, 100]}
                  tick={{ fill: theme.palette.text.secondary, fontSize: 12 }}
                  axisLine={false}
                  tickLine={false}
                />
                <RechartsTooltip
                  contentStyle={{
                    backgroundColor: theme.palette.background.paper,
                    border: `1px solid ${theme.palette.divider}`,
                    borderRadius: 8,
                    fontSize: 12,
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="score"
                  stroke={theme.palette.primary.main}
                  fill="url(#vhScoreGradient)"
                  strokeWidth={2}
                  dot={{ r: 4, fill: theme.palette.primary.main }}
                  activeDot={{ r: 6 }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </Box>
        </CardContent>
      </Card>

      {/* Timeline */}
      <Card>
        <CardContent sx={{ p: 2.5, "&:last-child": { pb: 2.5 } }}>
          <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 2 }}>
            Version Timeline
          </Typography>

          <Box sx={{ position: "relative", pl: 4 }}>
            {/* Vertical line */}
            <Box
              sx={{
                position: "absolute",
                left: 11,
                top: 0,
                bottom: 0,
                width: 2,
                backgroundColor: alpha(theme.palette.divider, 0.3),
                borderRadius: 1,
              }}
            />

            {versions.map((version, idx) => {
              const isExpanded = expandedId === version.id;
              const prevVersion = idx < versions.length - 1 ? versions[idx + 1] : null;
              const sc = scoreColor(version.aiScore);

              return (
                <motion.div
                  key={version.id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: idx * 0.08, duration: 0.3 }}
                >
                  <Box sx={{ position: "relative", mb: 2 }}>
                    {/* Timeline dot */}
                    <Box
                      sx={{
                        position: "absolute",
                        left: -28,
                        top: 16,
                        width: 10,
                        height: 10,
                        borderRadius: "50%",
                        backgroundColor: sc,
                        border: `2px solid ${theme.palette.background.paper}`,
                        boxShadow: `0 0 0 3px ${alpha(sc, 0.2)}`,
                        zIndex: 1,
                      }}
                    />

                    <Paper
                      elevation={0}
                      onClick={() => {
                        setExpandedId(isExpanded ? null : version.id);
                        onVersionSelect?.(version);
                      }}
                      sx={{
                        p: 2,
                        borderRadius: 2,
                        border: `1px solid ${alpha(
                          isExpanded ? theme.palette.primary.main : theme.palette.divider,
                          isExpanded ? 0.4 : 0.2
                        )}`,
                        cursor: "pointer",
                        transition: "all 0.2s",
                        "&:hover": {
                          borderColor: alpha(theme.palette.primary.main, 0.3),
                          backgroundColor: alpha(theme.palette.primary.main, 0.02),
                        },
                      }}
                    >
                      <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, flexWrap: "wrap" }}>
                        <Typography variant="body2" fontWeight={700}>
                          Version {version.versionNumber}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {formatDate(version.timestamp)}
                        </Typography>
                        <Box sx={{ flex: 1 }} />
                        <Chip
                          label={`AI: ${version.aiScore}%`}
                          size="small"
                          sx={{
                            backgroundColor: alpha(sc, 0.12),
                            color: sc,
                            fontWeight: 700,
                            fontSize: "0.7rem",
                          }}
                        />
                        <Chip
                          label={`${version.wordCount} words`}
                          size="small"
                          variant="outlined"
                          sx={{ fontSize: "0.7rem" }}
                        />
                        {prevVersion && (
                          <ScoreChangeBadge
                            current={version.aiScore}
                            previous={prevVersion.aiScore}
                          />
                        )}
                        <IconButton size="small">
                          {isExpanded ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
                        </IconButton>
                      </Box>

                      {/* Expanded diff */}
                      <AnimatePresence>
                        {isExpanded && version.diff && version.diff.length > 0 && (
                          <motion.div
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: "auto" }}
                            exit={{ opacity: 0, height: 0 }}
                            transition={{ duration: 0.3 }}
                          >
                            <Box sx={{ mt: 2 }}>
                              <Typography variant="caption" fontWeight={600} color="text.secondary" sx={{ mb: 1, display: "block" }}>
                                Changes from previous version
                              </Typography>
                              <DiffView segments={version.diff} />
                            </Box>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </Paper>
                  </Box>
                </motion.div>
              );
            })}
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
}
