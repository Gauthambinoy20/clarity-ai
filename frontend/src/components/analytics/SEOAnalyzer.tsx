import {
  Box,
  Typography,
  Card,
  CardContent,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  useTheme,
  Divider,
} from "@mui/material";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import CancelIcon from "@mui/icons-material/Cancel";
import ArrowUpwardIcon from "@mui/icons-material/ArrowUpward";
import { motion } from "framer-motion";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import type { SEOResult } from "@/types/analytics";

interface SEOAnalyzerProps {
  data: SEOResult;
}

function getGradeColor(grade: string): string {
  switch (grade) {
    case "A":
      return "#22c55e";
    case "B":
      return "#84cc16";
    case "C":
      return "#f59e0b";
    case "D":
      return "#f97316";
    case "F":
      return "#ef4444";
    default:
      return "#666";
  }
}

const priorityColors: Record<string, string> = {
  high: "#ef4444",
  medium: "#f59e0b",
  low: "#22c55e",
};

function SEOGauge({
  score,
  grade,
  size = 180,
}: {
  score: number;
  grade: string;
  size?: number;
}) {
  const theme = useTheme();
  const radius = (size - 20) / 2;
  const circumference = 2 * Math.PI * radius * 0.75;
  const strokeDashoffset = circumference - (score / 100) * circumference;
  const color = getGradeColor(grade);
  const center = size / 2;

  return (
    <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 1 }}>
      <Box sx={{ position: "relative", width: size, height: size }}>
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
          <circle
            cx={center}
            cy={center}
            r={radius}
            fill="none"
            stroke={theme.palette.divider}
            strokeWidth={8}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={circumference * 0.25}
            transform={`rotate(135 ${center} ${center})`}
          />
          <motion.circle
            cx={center}
            cy={center}
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth={8}
            strokeLinecap="round"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset }}
            transition={{ duration: 1.5, ease: "easeOut" }}
            transform={`rotate(135 ${center} ${center})`}
            style={{ filter: `drop-shadow(0 0 6px ${color}40)` }}
          />
        </svg>
        <Box
          sx={{
            position: "absolute",
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -45%)",
            textAlign: "center",
          }}
        >
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.4, type: "spring", stiffness: 200 }}
          >
            <Typography variant="h3" fontWeight={800} sx={{ color, lineHeight: 1 }}>
              {Math.round(score)}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              / 100
            </Typography>
          </motion.div>
        </Box>
      </Box>
      <Chip
        label={`Grade: ${grade}`}
        sx={{
          backgroundColor: `${color}20`,
          color,
          fontWeight: 700,
          fontSize: "1rem",
          px: 2,
        }}
      />
    </Box>
  );
}

const barColors = [
  "#7c3aed",
  "#06b6d4",
  "#ec4899",
  "#f59e0b",
  "#22c55e",
  "#3b82f6",
  "#8b5cf6",
  "#14b8a6",
  "#f43f5e",
  "#a855f7",
];

export default function SEOAnalyzer({ data }: SEOAnalyzerProps) {
  const theme = useTheme();

  const chartData = data.keywords.slice(0, 10).map((kw) => ({
    keyword: kw.keyword,
    count: kw.count,
    density: kw.density,
  }));

  return (
    <Box>
      {/* Header with gauge */}
      <Box
        sx={{
          display: "flex",
          flexDirection: { xs: "column", md: "row" },
          gap: 4,
          alignItems: "center",
          mb: 4,
        }}
      >
        <SEOGauge score={data.seoScore} grade={data.grade} />
        <Box sx={{ flex: 1 }}>
          <Typography variant="h6" fontWeight={600} gutterBottom>
            SEO Analysis Dashboard
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Your content has been evaluated across readability, keyword usage, structure,
            and optimization factors.
          </Typography>

          {/* Metrics Grid */}
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr", md: "1fr 1fr 1fr" },
              gap: 1.5,
            }}
          >
            {data.metrics.map((metric) => (
              <Card
                key={metric.name}
                variant="outlined"
                sx={{
                  borderColor: metric.pass ? "#22c55e40" : "#ef444440",
                }}
              >
                <CardContent sx={{ py: 1, px: 1.5, "&:last-child": { pb: 1 } }}>
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                    {metric.pass ? (
                      <CheckCircleIcon sx={{ color: "#22c55e", fontSize: 18 }} />
                    ) : (
                      <CancelIcon sx={{ color: "#ef4444", fontSize: 18 }} />
                    )}
                    <Box>
                      <Typography variant="caption" color="text.secondary" display="block">
                        {metric.name}
                      </Typography>
                      <Typography variant="body2" fontWeight={600}>
                        {typeof metric.value === "number"
                          ? metric.value % 1 === 0
                            ? metric.value
                            : metric.value.toFixed(1)
                          : metric.value}
                        {metric.unit}
                      </Typography>
                      <Typography
                        variant="caption"
                        color="text.secondary"
                        sx={{ fontSize: "0.65rem" }}
                      >
                        Target: {metric.target}
                      </Typography>
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            ))}
          </Box>
        </Box>
      </Box>

      <Divider sx={{ mb: 3 }} />

      {/* Keyword Distribution Chart */}
      {chartData.length > 0 && (
        <Box sx={{ mb: 4 }}>
          <Typography variant="subtitle1" fontWeight={600} gutterBottom>
            Keyword Distribution
          </Typography>
          <Card variant="outlined">
            <CardContent>
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 40 }}>
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke={theme.palette.divider}
                  />
                  <XAxis
                    dataKey="keyword"
                    tick={{ fontSize: 11, fill: theme.palette.text.secondary }}
                    angle={-35}
                    textAnchor="end"
                  />
                  <YAxis
                    tick={{ fontSize: 11, fill: theme.palette.text.secondary }}
                    label={{
                      value: "Count",
                      angle: -90,
                      position: "insideLeft",
                      style: { fill: theme.palette.text.secondary, fontSize: 12 },
                    }}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: theme.palette.background.paper,
                      border: `1px solid ${theme.palette.divider}`,
                      borderRadius: 8,
                      fontSize: 13,
                    }}
                    formatter={(value: number, _name: string, props: { payload: { density: number } }) => [
                      `${value} (${props.payload.density.toFixed(2)}%)`,
                      "Occurrences",
                    ]}
                  />
                  <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                    {chartData.map((_entry, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={barColors[index % barColors.length]}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Box>
      )}

      {/* Keyword Density Table */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="subtitle1" fontWeight={600} gutterBottom>
          Keyword Density
        </Typography>
        <TableContainer component={Card} variant="outlined">
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell sx={{ fontWeight: 600 }}>Keyword</TableCell>
                <TableCell align="right" sx={{ fontWeight: 600 }}>
                  Count
                </TableCell>
                <TableCell align="right" sx={{ fontWeight: 600 }}>
                  Density (%)
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {data.keywords.map((kw) => (
                <TableRow key={kw.keyword} hover>
                  <TableCell>
                    <Typography variant="body2" fontWeight={500}>
                      {kw.keyword}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">{kw.count}</TableCell>
                  <TableCell align="right">{kw.density.toFixed(2)}%</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Box>

      {/* Recommendations */}
      {data.recommendations.length > 0 && (
        <Box>
          <Typography variant="subtitle1" fontWeight={600} gutterBottom>
            Recommendations
          </Typography>
          <Card variant="outlined">
            <List dense>
              {data.recommendations.map((rec, i) => (
                <ListItem key={i} divider={i < data.recommendations.length - 1}>
                  <ListItemIcon sx={{ minWidth: 36 }}>
                    <ArrowUpwardIcon
                      sx={{
                        color: priorityColors[rec.priority],
                        fontSize: 18,
                      }}
                    />
                  </ListItemIcon>
                  <ListItemText
                    primary={rec.text}
                    primaryTypographyProps={{ variant: "body2" }}
                  />
                  <Chip
                    label={rec.priority}
                    size="small"
                    sx={{
                      backgroundColor: `${priorityColors[rec.priority]}20`,
                      color: priorityColors[rec.priority],
                      fontWeight: 600,
                      textTransform: "capitalize",
                    }}
                  />
                </ListItem>
              ))}
            </List>
          </Card>
        </Box>
      )}
    </Box>
  );
}
